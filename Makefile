.PHONY: setup run clean test lint format help

help:
	@echo "Available commands:"
	@echo "  make setup    - Install dependencies and create config"
	@echo "  make run      - Run the monitor"
	@echo "  make clean    - Remove generated files"
	@echo "  make test     - Run syntax check"
	@echo "  make format   - Format code with black"
	@echo "  make lint     - Run linting"

setup:
	@echo "Setting up HKEX Monitor..."
	@if [ ! -f config.json ]; then \
		cp config.json.example config.json; \
		echo "✓ Created config.json - please edit with your credentials"; \
	fi
	@./run.sh setup

run:
	@./run.sh

clean:
	@echo "Cleaning up..."
	@rm -rf __pycache__ .venv *.pyc .pytest_cache
	@rm -f listings_state.json hkex_monitor.log
	@echo "✓ Cleaned (config.json preserved)"

test:
	@python3 -m py_compile hkex_monitor.py
	@echo "✓ Syntax check passed"

format:
	@which black > /dev/null || pip install black
	@black hkex_monitor.py

lint:
	@which flake8 > /dev/null || pip install flake8
	@flake8 hkex_monitor.py --max-line-length=100
