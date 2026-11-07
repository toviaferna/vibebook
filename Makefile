.PHONY: sync test lint format typecheck check build run web-install web-dev web-build web-test web-lint web-check check-all sidecar

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

check: lint typecheck test

build:
	uv build

run:
	uv run vibebook --help

web-install:
	cd web && npm ci

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

web-test:
	cd web && npm run test

web-lint:
	cd web && npm run lint

web-check: web-lint web-test web-build

check-all: check web-check

sidecar:
	cd web && npm run build
	uv run pyinstaller packaging/pyinstaller/vibebook-sidecar.spec --noconfirm
