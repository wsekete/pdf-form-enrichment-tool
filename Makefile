# PDF Form Enrichment Tool - Professional Makefile

.PHONY: help install install-dev test test-cov lint format type-check security clean build docs docker run-dev

# Default target
help:
	@echo "PDF Form Enrichment Tool - Available Commands:"
	@echo ""
	@echo "Development Setup:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  setup         Complete development environment setup"
	@echo ""
	@echo "Code Quality:"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  lint          Run all linters"
	@echo "  format        Format code with black and isort"
	@echo "  type-check    Run type checking with mypy"
	@echo "  security      Run security checks"
	@echo "  quality       Run all quality checks"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build package"
	@echo "  docs          Build documentation"
	@echo "  docker        Build Docker images"
	@echo ""
	@echo "Development:"
	@echo "  run-dev       Start development server"
	@echo "  shell         Start IPython shell with project loaded"

# Installation
install:
	pip install -r requirements.txt
	pip install -e .

install-dev: install
	pip install -r requirements-dev.txt
	pre-commit install

setup: install-dev
	@echo "Setting up development environment..."
	mkdir -p temp logs output
	cp .env.example .env
	@echo "✅ Development environment ready!"
	@echo "📝 Please edit .env with your API keys"

# Testing
test:
	pytest -v

test-cov:
	pytest --cov=pdf_form_editor --cov-report=html --cov-report=term-missing --cov-fail-under=90

test-performance:
	pytest tests/performance/ -v --benchmark-only

test-integration:
	pytest tests/integration/ -v

test-all: test test-integration test-performance

# Code Quality
lint:
	flake8 pdf_form_editor tests
	pylint pdf_form_editor
	bandit -r pdf_form_editor

format:
	black pdf_form_editor tests
	isort pdf_form_editor tests

type-check:
	mypy pdf_form_editor --ignore-missing-imports

security:
	bandit -r pdf_form_editor -f json -o security-report.json
	safety check --json --output safety-report.json

quality: format lint type-check security test-cov
	@echo "✅ All quality checks passed!"

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Build
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8080

# Docker
docker:
	docker build -t pdf-form-enrichment-tool .

docker-dev:
	docker-compose up -d pdf-form-editor

docker-prod:
	docker-compose --profile production up -d

# Development utilities
run-dev:
	python -m pdf_form_editor.mcp_server --debug

shell:
	ipython -c "import pdf_form_editor; print('PDF Form Enrichment Tool loaded')"

# Sample workflows
process-sample:
	python -m pdf_form_editor process tests/fixtures/sample_form.pdf --review

analyze-sample:
	python -m pdf_form_editor analyze tests/fixtures/sample_form.pdf

batch-sample:
	python -m pdf_form_editor batch tests/fixtures/*.pdf --output output/

# CI/CD helpers
ci-install:
	pip install -r requirements.txt -r requirements-dev.txt

ci-test:
	pytest --cov=pdf_form_editor --cov-report=xml --cov-fail-under=90

ci-quality:
	black --check pdf_form_editor tests
	flake8 pdf_form_editor tests
	mypy pdf_form_editor --ignore-missing-imports
	bandit -r pdf_form_editor

# Performance profiling
profile:
	python -m cProfile -o profile.stats -m pdf_form_editor process tests/fixtures/complex_form.pdf
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('tottime').print_stats(20)"

memory-profile:
	mprof run python -m pdf_form_editor process tests/fixtures/large_form.pdf
	mprof plot

# Environment management
env-check:
	@echo "🔍 Environment Check:"
	@python --version
	@pip --version
	@echo "📦 Installed packages:"
	@pip list | grep -E "(pypdf|openai|click|pydantic)"

# Cleanup operations
clean-logs:
	find logs/ -name "*.log" -mtime +30 -delete

clean-temp:
	rm -rf temp/*

clean-cache:
	rm -rf .cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete

# Full reset
reset: clean clean-logs clean-temp clean-cache
	@echo "🧹 Full cleanup completed"
