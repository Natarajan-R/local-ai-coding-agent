.PHONY: help venv setup install run serve bench test lint clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Available commands:"
	@echo "  make setup   - Create venv and install dev dependencies (editable)"
	@echo "  make run      - Run the agent (TASK=\"...\")"
	@echo "  make serve    - Launch the web dashboard"
	@echo "  make bench    - Run benchmark tasks"
	@echo "  make test     - Run the test suite"
	@echo "  make lint     - Lint with ruff"
	@echo "  make clean    - Remove caches and the virtualenv"

$(VENV):
	python3 -m venv $(VENV)

venv: $(VENV)

setup: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

run:
	$(PY) -m agent.cli.main run "$(TASK)"

serve:
	$(PY) -m agent.cli.main serve

bench:
	$(PY) -m agent.cli.main bench

test:
	$(PY) -m pytest

lint:
	$(VENV)/bin/ruff check src tests

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
