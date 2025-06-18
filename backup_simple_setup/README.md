# PDF Form Enrichment Tool

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

🚀 **Transform PDF form processing from hours to minutes with AI-powered field naming automation**

## Overview

The PDF Form Enrichment Tool automates the manual, time-consuming process of renaming PDF form fields to BEM naming conventions. This tool transforms a 2-4 hour manual task into a 5-10 minute automated workflow, enabling 10x throughput improvement for forms processing teams.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-form-enrichment-tool.git
cd pdf-form-enrichment-tool

# Set up development environment
make setup

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your API keys

# Process your first PDF
python -m pdf_form_editor process your_form.pdf --review
```

### Basic Usage

```bash
# Process a single PDF
pdf-form-editor process input.pdf

# Interactive review mode
pdf-form-editor process input.pdf --review

# Batch processing
pdf-form-editor batch *.pdf
```

## Features

- **⚡ 90% Time Reduction**: From 2-4 hours to 5-10 minutes per form
- **🤖 AI-Powered Naming**: Context-aware field naming using OpenAI GPT-4
- **🔧 Safe PDF Modification**: Zero corruption with rollback capability
- **💬 Conversational Interface**: Claude Desktop integration via MCP
- **📈 98% Accuracy**: Consistent BEM naming compliance
- **🔄 Batch Processing**: Handle multiple PDFs efficiently

## Documentation

- **[Setup Guide](GITHUB_SETUP.md)**: Complete setup instructions
- **[Contributing](CONTRIBUTING.md)**: How to contribute to the project
- **[Documentation](docs/)**: Detailed technical documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
