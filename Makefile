PY ?= python3

.PHONY: venv install playwright fmt lint type type-mypy arch test check precommit

venv:
	$(PY) -m venv .venv

install:
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e ".[admin,dev]"

playwright:
	$(PY) -m playwright install

fmt:
	$(PY) -m ruff format .

lint:
	$(PY) -m ruff check .

type:
	$(PY) -m pyright

type-mypy:
	$(PY) -m mypy .

arch:
	lint-imports

test:
	$(PY) -m pytest

check: lint type arch test

precommit:
	$(PY) -m pre_commit install
