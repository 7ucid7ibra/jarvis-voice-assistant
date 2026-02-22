.PHONY: run test test-compile coverage lint format build clean refresh-deps

PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

# --- Setup -------------------------------------------------------------------

.venv/bin/activate: requirements.txt requirements-dev.txt
	python3.11 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

# --- Run ---------------------------------------------------------------------

run: .venv/bin/activate
	$(PYTHON) run.py

# --- Tests -------------------------------------------------------------------

test: .venv/bin/activate
	$(PYTHON) -m pytest tests/ -v --tb=short

test-compile: .venv/bin/activate
	$(PYTHON) -m py_compile jarvis_assistant/*.py
	@echo "All modules compile OK"

coverage: .venv/bin/activate
	$(PYTHON) -m pytest tests/ --cov=jarvis_assistant --cov-report=term-missing

# --- Code quality ------------------------------------------------------------

lint: .venv/bin/activate
	$(PYTHON) -m ruff check jarvis_assistant/ tests/

format: .venv/bin/activate
	$(PYTHON) -m ruff format jarvis_assistant/ tests/

# --- Build -------------------------------------------------------------------

build: .venv/bin/activate
	$(PYTHON) -m PyInstaller "Jarvis Assistant.spec"

# --- Maintenance -------------------------------------------------------------

clean:
	rm -rf build/ dist/ \
	       __pycache__ jarvis_assistant/__pycache__ tests/__pycache__ \
	       .pytest_cache .coverage htmlcov/

refresh-deps: .venv/bin/activate
	$(PIP) install -r requirements.txt
	$(PIP) freeze > requirements.lock.txt
	@echo "requirements.lock.txt updated — review and commit it"
