.PHONY: format-check format pyright ruff

lint-all: format sort-imports pyright

format-check:
	poetry run ruff format --check

format:
	poetry run ruff format

pyright:
	poetry run pyright

ruff:
	poetry run ruff check .

ruff-fix:
	poetry run ruff check . --fix

sort-imports:
	ruff check --select I --fix

check: format-check ruff pyright