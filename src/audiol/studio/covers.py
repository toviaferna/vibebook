# ruff: noqa: E501
from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

_PALETTES = [
    ("#efe6d5", "#26221d", "#5b2022", "#a68447", "#40505b"),
    ("#e8e0d1", "#24221f", "#283747", "#b08a4f", "#6b7b6b"),
    ("#e6dfd2", "#1f2a2a", "#2f5d62", "#b59a6a", "#5f6b76"),
    ("#f0e8d9", "#2e2822", "#7a3b2e", "#c19a5b", "#4c5d63"),
]


def _seed(*values: str) -> int:
    payload = "\x00".join(value.strip().lower() for value in values)
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)


def _wrap(title: str, width: int = 16) -> list[str]:
    words = title.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:4] or ["Libro"]


def generated_cover(title: str, author: str) -> str:
    seed = _seed(title, author)
    paper, ink, spine, brass, muted = _PALETTES[seed % len(_PALETTES)]
    lines = _wrap(title)
    title_size = 92 if max(len(line) for line in lines) <= 14 else 78
    title_y = 300
    title_markup = "".join(
        f'<tspan x="132" dy="{0 if index == 0 else title_size + 10}">{escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    rule_y = title_y + (title_size + 10) * len(lines) + 22
    author_y = rule_y + 58
    variant = seed % 4
    motif = _motif(variant, spine, brass, muted)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1800" viewBox="0 0 1200 1800">
  <title>{escape(title)} — {escape(author)}</title>
  <rect width="1200" height="1800" fill="{paper}"/>
  <g opacity=".18" stroke="{ink}" stroke-width="1">
    {"".join(f'<line x1="0" y1="{y}" x2="1200" y2="{y}"/>' for y in range(12, 1800, 7))}
  </g>
  <rect width="92" height="1800" fill="{spine}"/>
  <rect x="92" width="5" height="1800" fill="{brass}"/>
  <text x="132" y="92" font-family="Georgia, 'Times New Roman', serif" font-size="24" font-weight="700" letter-spacing="3" fill="{brass}">VIBEBOOK · BIBLIOTECA</text>
  <text x="132" y="{title_y}" font-family="Georgia, 'Times New Roman', serif" font-size="{title_size}" font-weight="700" fill="{ink}">{title_markup}</text>
  <line x1="132" y1="{rule_y}" x2="650" y2="{rule_y}" stroke="{brass}" stroke-width="3"/>
  <text x="132" y="{author_y}" font-family="Georgia, 'Times New Roman', serif" font-size="38" letter-spacing="2" fill="{muted}">{escape(author.upper())}</text>
  <text x="132" y="{author_y + 52}" font-family="Georgia, 'Times New Roman', serif" font-size="22" font-weight="700" letter-spacing="4" fill="{brass}">LECTURA</text>
  {motif}
  <text x="132" y="1706" font-family="Georgia, 'Times New Roman', serif" font-size="21" letter-spacing="3" fill="{brass}">VB · {seed % 97:02d}</text>
</svg>
"""


def _motif(variant: int, spine: str, brass: str, muted: str) -> str:
    if variant == 0:
        arcs = "".join(
            f'<path d="M {700 - index * 16} 1530 A {250 + index * 16} {210 + index * 16} 0 0 1 {1160 + index * 16} 1530" fill="none" stroke="{muted if index % 2 else brass}" stroke-width="5" opacity=".8"/>'
            for index in range(4)
        )
        return arcs
    if variant == 1:
        return (
            f'<circle cx="930" cy="1320" r="116" fill="none" stroke="{brass}" stroke-width="6"/>'
            f'<line x1="120" y1="1520" x2="1120" y2="1520" stroke="{muted}" stroke-width="4"/>'
            f'<line x1="120" y1="1570" x2="980" y2="1570" stroke="{spine}" stroke-width="2" opacity=".6"/>'
        )
    if variant == 2:
        lines = "".join(
            f'<line x1="{760 + index * 44}" y1="{1250 + index * 22}" x2="{760 + index * 44}" y2="1570" stroke="{brass if index % 2 else muted}" stroke-width="4" opacity=".75"/>'
            for index in range(7)
        )
        return lines + f'<circle cx="860" cy="1190" r="42" fill="{spine}" opacity=".8"/>'
    return (
        f'<path d="M 620 1570 L 820 1320 L 960 1570 Z" fill="none" stroke="{brass}" stroke-width="5"/>'
        f'<path d="M 790 1570 L 950 1390 L 1110 1570 Z" fill="{spine}" opacity=".18" stroke="{spine}" stroke-width="2"/>'
        f'<line x1="120" y1="1570" x2="1120" y2="1570" stroke="{muted}" stroke-width="3"/>'
    )


def write_generated_cover(title: str, author: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "cover.svg"
    output.write_text(generated_cover(title, author), encoding="utf-8")
    return output
