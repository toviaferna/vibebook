"""Read-only Git preflight for a branch you are about to push or merge.

It does not mutate the repository. Run it before committing a conflict
resolution, before opening a PR, and after updating a branch from main.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

CONFLICT_MARKERS = re.compile(r"^(<{7}|={7}|>{7})(?: |$)")
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def main() -> int:
    problems: list[str] = []
    warnings: list[str] = []

    branch = git("branch", "--show-current")
    if not branch:
        problems.append("HEAD está detached; creá o cambiá a una rama antes de continuar.")
    elif branch == "main":
        problems.append("Estás en main: creá una rama antes de commitear.")
    elif "/" not in branch:
        warnings.append(f"La rama {branch!r} no usa un prefijo feat/, fix/, docs/ o chore/.")

    status = git("status", "--porcelain")
    if any(
        line.startswith(("UU", "AA", "DD", "AU", "UA", "DU", "UD")) for line in status.splitlines()
    ):
        problems.append("Hay archivos sin resolver en el índice (merge/rebase en curso).")

    for path in git("diff", "--name-only", "--diff-filter=ACMRTUXB").splitlines():
        candidate = Path(path)
        if candidate.suffix.lower() not in TEXT_SUFFIXES or not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if CONFLICT_MARKERS.match(line):
                problems.append(f"Marcador de conflicto en {path}:{number}.")
                break

    diff_check = subprocess.run(
        ["git", "diff", "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if diff_check.returncode != 0:
        problems.append(diff_check.stdout.strip() or "git diff --check encontró problemas.")

    try:
        counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}").split()
        ahead, behind = (int(value) for value in counts)
        if behind:
            warnings.append(f"La rama está {behind} commits detrás de su upstream.")
        if ahead:
            warnings.append(f"La rama tiene {ahead} commits locales sin pushear.")
    except (RuntimeError, ValueError):
        warnings.append("La rama no tiene upstream configurado.")

    print(f"branch: {branch or '(detached)'}")
    print(f"worktrees: {len(git('worktree', 'list').splitlines())}")
    for warning in warnings:
        print(f"warning: {warning}")
    for problem in problems:
        print(f"error: {problem}")
    if problems:
        return 1
    print("preflight: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
