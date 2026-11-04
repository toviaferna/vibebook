.PHONY: sync test lint format typecheck check build run

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
