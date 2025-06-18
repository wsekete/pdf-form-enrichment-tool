# PDF Form Enrichment Tool - Makefile

.PHONY: help setup install test clean

help:
	@echo "PDF Form Enrichment Tool - Available Commands:"
	@echo "  setup       Complete development environment setup"
	@echo "  install     Install dependencies"
	@echo "  test        Run tests (once implemented)"
	@echo "  clean       Clean build artifacts"

setup:
	@echo "Setting up development environment..."
	python -m venv venv
	@echo "✅ Virtual environment created!"
	@echo "📝 Next steps:"
	@echo "   1. Activate virtual environment:"
	@echo "      - Windows: venv\Scripts\activate"
	@echo "      - Mac/Linux: source venv/bin/activate"
	@echo "   2. Install dependencies: make install"
	@echo "   3. Copy .env.example to .env and add your API keys"

install:
	pip install -r requirements.txt
	pip install -e .

test:
	@echo "🚧 Tests will be implemented following the task list"

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ .pytest_cache/
