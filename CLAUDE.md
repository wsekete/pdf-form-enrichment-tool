# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The PDF Form Enrichment Tool is an AI-powered Python application that automates the process of renaming PDF form fields to BEM (Block Element Modifier) naming conventions. It transforms a 2-4 hour manual task into a 5-10 minute automated workflow, providing 10x throughput improvement for forms processing teams.

## Architecture

The project follows a modular architecture with these core components:

- **pdf_form_editor/**: Main package containing all core functionality
  - **ai/**: AI integration modules for OpenAI GPT-4 powered field naming  
  - **core/**: Core PDF processing logic (parsing, field extraction, modification)
  - **mcp_server/**: MCP (Model Context Protocol) server for Claude Desktop integration
  - **utils/**: Utility modules for logging, error handling, and common functions
- **tests/**: Comprehensive test suite with unit, integration, and performance tests
- **config/**: Configuration files (default.yaml contains app settings)
- **training_data/**: BEM naming patterns and training data for AI model
- **docs/**: Complete documentation including PRDs and API references

## Common Development Commands

### Setup and Installation
```bash
# Complete development environment setup
make setup

# Install production dependencies only
make install

# Install development dependencies
make install-dev
```

### Testing
```bash
# Run all tests
make test

# Run tests with coverage report (minimum 90% required)
make test-cov

# Run specific test types
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests  
pytest tests/performance/    # Performance tests
pytest -m ai                # AI-dependent tests
pytest -m mcp               # MCP server tests
```

### Code Quality
```bash
# Run all quality checks (format, lint, type-check, security, test-cov)
make quality

# Individual quality checks
make format      # Format with black and isort
make lint        # Run flake8, pylint, bandit
make type-check  # Run mypy type checking
make security    # Run bandit and safety checks
```

### Development Tools
```bash
# Start MCP server in debug mode
make run-dev

# Process sample PDF with review mode
make process-sample

# Profile performance
make profile

# Clean all build artifacts
make clean
```

## Key Configuration

- **config/default.yaml**: Main configuration file with AI settings, processing parameters, and MCP server config
- **pytest.ini**: Test configuration with markers for different test types (unit, integration, performance, ai, mcp)
- **requirements.txt**: Production dependencies including PyPDF, OpenAI, Click, Pydantic
- **requirements-dev.txt**: Development dependencies for testing, linting, profiling

## BEM Naming Convention

The tool implements BEM (Block Element Modifier) naming:
- **Format**: `block_element__modifier`
- **Example**: `owner-information_name__first`, `payment_amount__gross`
- **Configuration**: Controlled by `naming` section in config/default.yaml

## AI Integration

- Uses OpenAI GPT-4 for contextual field naming
- Training data stored in `training_data/bem_patterns.json`
- AI settings configurable in `config/default.yaml` under `ai` section
- Requires `OPENAI_API_KEY` environment variable

## MCP Server Integration

The MCP server enables Claude Desktop integration:
- Entry point: `python -m pdf_form_editor.mcp_server`
- Configuration template provided in README.md
- Requires environment variables: `OPENAI_API_KEY`, `ADOBE_API_KEY`

## Development Status

The project is currently in early development with basic CLI structure in place. Core PDF processing, AI integration, and MCP server functionality are outlined in the task lists but not yet implemented. Follow the development phases in `docs/form_field_editor_prd.md` for implementation priorities.