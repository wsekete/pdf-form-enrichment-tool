#!/usr/bin/env python3
"""
PDF Form Enrichment Tool - Project Setup Script

This script automatically creates the complete project structure with all files.
Run this after cloning your empty GitHub repository.

Usage:
    python setup_project.py
"""

import os
import sys
from pathlib import Path

def create_directory_structure():
    """Create the complete directory structure."""
    directories = [
        "pdf_form_editor",
        "pdf_form_editor/core",
        "pdf_form_editor/ai", 
        "pdf_form_editor/mcp_server",
        "pdf_form_editor/utils",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/performance",
        "tests/fixtures",
        "docs",
        "training_data",
        "config",
        ".github",
        ".github/workflows",
        "logs",
        "temp",
        "output"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_file_with_content(filepath, content):
    """Create a file with the given content."""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created file: {filepath}")
    except Exception as e:
        print(f"❌ Error creating {filepath}: {e}")

def create_all_files():
    """Create all project files with their content."""
    
    # README.md
    readme_content = '''# PDF Form Enrichment Tool

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
'''
    
    # setup.py
    setup_content = '''#!/usr/bin/env python3
"""PDF Form Enrichment Tool Setup"""

from setuptools import setup, find_packages

setup(
    name="pdf-form-enrichment-tool",
    version="1.0.0",
    author="Your Company",
    description="AI-powered PDF form field enrichment with BEM naming automation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pypdf>=4.0.0",
        "click>=8.0.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0.0",
        "python-dotenv>=1.0.0",
        "openai>=1.30.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "pdf-form-editor=pdf_form_editor.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
'''
    
    # requirements.txt
    requirements_content = '''pypdf>=4.0.0
click>=8.0.0
pydantic>=2.0.0
pyyaml>=6.0.0
python-dotenv>=1.0.0
openai>=1.30.0
requests>=2.31.0
aiohttp>=3.9.0
pandas>=2.0.0
numpy>=1.24.0
python-dateutil>=2.8.0
structlog>=23.0.0
rich>=13.0.0
'''

    # .env.example
    env_example_content = '''# PDF Form Enrichment Tool Environment Variables
# Copy this file to .env and fill in your actual values

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=150
OPENAI_TEMPERATURE=0.1

# Adobe PDF Services (Optional)
ADOBE_API_KEY=your_adobe_api_key_here
ADOBE_CLIENT_SECRET=your_adobe_client_secret_here

# Application Configuration
LOG_LEVEL=INFO
DEBUG=false
CONFIDENCE_THRESHOLD=0.8
AUTO_APPROVE_HIGH_CONFIDENCE=false
'''

    # .gitignore
    gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.cache
nosetests.xml
coverage.xml

# Logs
logs/
*.log

# PDF Form Editor specific
temp/
tmp/
*_parsed.pdf
output/
processed/
config/local.yaml
config/production.yaml
adobe_credentials.json
api_keys.txt
secrets/

# OS
.DS_Store
.DS_Store?
._*
Thumbs.db
ehthumbs.db
'''

    # Basic __init__.py files
    init_content = '''"""PDF Form Enrichment Tool"""

__version__ = "1.0.0"
'''
    
    # Simple CLI placeholder
    cli_content = '''#!/usr/bin/env python3
"""Command Line Interface for PDF Form Enrichment Tool"""

import click

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """PDF Form Enrichment Tool - AI-powered BEM naming automation."""
    pass

@cli.command()
@click.argument("pdf_path")
def process(pdf_path):
    """Process a PDF form with BEM naming."""
    click.echo(f"Processing PDF: {pdf_path}")
    click.echo("🚧 Implementation coming soon! Follow the task list to build this.")

def main():
    cli()

if __name__ == "__main__":
    main()
'''

    # Makefile
    makefile_content = '''# PDF Form Enrichment Tool - Makefile

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
	@echo "      - Windows: venv\\Scripts\\activate"
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
'''

    # Files to create
    files = {
        "README.md": readme_content,
        "setup.py": setup_content,
        "requirements.txt": requirements_content,
        ".env.example": env_example_content,
        ".gitignore": gitignore_content,
        "pdf_form_editor/__init__.py": init_content,
        "pdf_form_editor/cli.py": cli_content,
        "pdf_form_editor/core/__init__.py": init_content,
        "pdf_form_editor/ai/__init__.py": init_content,
        "pdf_form_editor/mcp_server/__init__.py": init_content,
        "pdf_form_editor/utils/__init__.py": init_content,
        "tests/__init__.py": "",
        "Makefile": makefile_content,
        "LICENSE": '''MIT License

Copyright (c) 2024 Your Company Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.''',
    }
    
    # Create all files
    for filepath, content in files.items():
        create_file_with_content(filepath, content)

def main():
    """Main setup function."""
    print("🚀 Setting up PDF Form Enrichment Tool...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path(".git").exists():
        print("❌ Error: This doesn't look like a Git repository.")
        print("💡 Make sure you've cloned your GitHub repository first:")
        print("   git clone https://github.com/YOUR_USERNAME/pdf-form-enrichment-tool.git")
        print("   cd pdf-form-enrichment-tool")
        print("   python setup_project.py")
        sys.exit(1)
    
    print("📁 Creating directory structure...")
    create_directory_structure()
    
    print("\n📄 Creating project files...")
    create_all_files()
    
    print("\n" + "=" * 50)
    print("✅ Project setup complete!")
    print("\n🎯 Next steps:")
    print("1. Set up your environment:")
    print("   make setup")
    print("2. Activate virtual environment:")
    print("   - Windows: venv\\Scripts\\activate")
    print("   - Mac/Linux: source venv/bin/activate")
    print("3. Install dependencies:")
    print("   make install")
    print("4. Copy .env.example to .env and add your API keys")
    print("5. Commit your changes:")
    print("   git add .")
    print("   git commit -m 'Initial project setup'")
    print("   git push origin main")
    print("\n🚀 Ready to start building your PDF tool!")

if __name__ == "__main__":
    main()
