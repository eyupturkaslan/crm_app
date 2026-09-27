.PHONY: install run seed test lint fmt

install:
	python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

run:
	.venv/bin/python manage.py migrate && .venv/bin/python manage.py runserver

seed:
	.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

fmt:
	.venv/bin/ruff check --fix . && .venv/bin/ruff format .
