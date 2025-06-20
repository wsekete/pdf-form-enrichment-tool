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
- **training/**: Training data integration and pattern analysis for BEM name learning
- **samples/**: Training data directory containing CSV/PDF pairs and FormField_examples.csv
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

**Phase 1: Foundation & Core Parsing** - ✅ **100% COMPLETE**
- ✅ **Task 1.1**: Project Setup & Environment (COMPLETED)
- ✅ **Task 1.2**: PDF Analysis with comprehensive metadata extraction (COMPLETED)
- ✅ **Task 1.3**: Form Field Discovery with radio button hierarchy breakthrough (COMPLETED)
- ✅ **Task 1.4**: Field Context Extraction with AI-ready output (COMPLETED)

**Phase 2: BEM Name Generation & PDF Modification** - 🔄 **IN PROGRESS**
- ✅ **Task 2.1**: Training Data Integration & Pattern Analysis (COMPLETED)
- ⏳ **Task 2.2**: Context-Aware BEM Name Generator (PENDING)
- ⏳ **Task 2.3**: PDF Field Modification Engine (PENDING)  
- ⏳ **Task 2.4**: Database-Ready Output Generation (PENDING)

**Major Breakthroughs**: 
1. Complete form field extraction including both radio group containers AND individual radio button widgets, achieving 100% accuracy on real-world forms (98/98 fields detected in test form FAFF-0009AO.13).
2. Intelligent context extraction with 75%+ confidence on complex forms, providing rich semantic data for AI naming.
3. **NEW**: Training data integration system processes 8,264 field mappings from 14 PDF/CSV pairs + FormField_examples.csv, extracting 1,028 naming patterns for intelligent BEM generation.

**Task 2.1 Complete**: Comprehensive training data integration and pattern analysis system built. Successfully processes all training pairs with 450.9% increase in data volume through FormField_examples.csv integration. Pattern database ready for intelligent BEM name generation.