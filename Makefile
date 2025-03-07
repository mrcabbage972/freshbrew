.PHONY: format-check format pyright ruff

lint-all: format pyright

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

check: format-check ruff pyright