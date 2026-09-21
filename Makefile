# NEXUS — developer convenience targets
#
# Usage:
#   make setup           – create/recreate venv with the best available Python
#   make setup PYTHON=python3.11  – force a specific interpreter
#   make run             – start the Streamlit app
#   make test            – run unit tests (no Snowflake credentials required)
#   make lint            – syntax-check all Python source files
#   make clean           – remove the venv

PYTHON   ?= $(shell command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || command -v python3 2>/dev/null)
VENV_DIR  = app/venv
PIP       = $(VENV_DIR)/bin/pip
STREAMLIT = $(VENV_DIR)/bin/streamlit
PYTEST    = $(VENV_DIR)/bin/pytest

.PHONY: setup run test lint clean check-python

## Check the Python version and warn if < 3.11
check-python:
	@PY_VER="$$("$(PYTHON)" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)"; \
	MAJOR=$$(echo $$PY_VER | cut -d. -f1); \
	MINOR=$$(echo $$PY_VER | cut -d. -f2); \
	if [ "$$MAJOR" -lt 3 ] || ( [ "$$MAJOR" -eq 3 ] && [ "$$MINOR" -lt 11 ] ); then \
		echo "⚠  WARNING: Python $$PY_VER is below 3.11 (EOL for Snowflake)."; \
		echo "   Install Python 3.11+ and run: make setup PYTHON=python3.11"; \
		echo "   macOS: brew install python@3.11  OR  https://www.python.org/downloads/"; \
	else \
		echo "✓  Python $$PY_VER — OK"; \
	fi

## Create / recreate the virtual environment
setup: check-python
	@echo "Creating venv at $(VENV_DIR) using $(PYTHON)..."
	$(PYTHON) -m venv --clear $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r app/requirements.txt
	@echo ""
	@echo "✓  Setup complete. Copy secrets template if needed:"
	@echo "   cp app/.streamlit/secrets.toml.example app/.streamlit/secrets.toml"
	@echo "   Then: make run"

## Start the Streamlit app
run:
	@if [ ! -f app/.streamlit/secrets.toml ]; then \
		echo "⚠  Missing app/.streamlit/secrets.toml — copy from secrets.toml.example and fill in your credentials."; \
		exit 1; \
	fi
	cd app && $(CURDIR)/$(STREAMLIT) run streamlit_app.py

## Run unit tests (no Snowflake credentials required)
test:
	cd app && $(CURDIR)/$(PYTEST) ../tests/ -v

## Syntax-check all Python source files
lint:
	@$(PYTHON) -c " \
import ast, sys, os; \
files = [ \
    'app/services/snowflake.py', 'app/services/agent.py', \
    'app/components/chat.py', 'app/components/kpi_cards.py', \
    'app/components/scenario_panel.py', 'app/components/dependency_graph.py', \
    'app/components/impact_details.py', 'app/components/mitigation_table.py', \
    'app/components/evidence.py', 'app/streamlit_app.py', \
    'app/ui/theme.py', 'tests/test_utils.py', \
]; \
ok = True; \
[print('OK ', f) or True if not (setattr(sys, '_', ast.parse(open(f).read())) or False) \
 else print('FAIL', f) or setattr(ok, 'v', False) for f in files]; \
sys.exit(0) \
"

## Remove the virtual environment
clean:
	rm -rf $(VENV_DIR)
	@echo "Removed $(VENV_DIR)"
