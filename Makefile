.PHONY: format-check format pyright ruff

lint-all: format ruff-fix sort-imports pyright

format-notebooks:
	poetry run nbqa isort . && poetry run nbqa ruff . --fix

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
	poetry run ruff check --select I --fix

check: format-check ruff pyright