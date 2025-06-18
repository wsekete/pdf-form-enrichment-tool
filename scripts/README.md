# Setup Scripts

This directory contains setup and utility scripts for the PDF Form Enrichment Tool project.

## 📋 Script Overview

These scripts help you set up a complete, professional development environment for building your PDF form processing tool.

### 🛠️ Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `setup_script.py` | Basic project setup | First time setup, creates minimal structure |
| `upgrade_to_professional.py` | Professional upgrade | After basic setup, adds enterprise tools |
| `add_comprehensive_docs.py` | Complete documentation | Adds detailed task lists and guides |

## 🚀 Quick Start

### For New Projects (Recommended Path)

```bash
# 1. Clone your repository
git clone https://github.com/yourusername/pdf-form-enrichment-tool.git
cd pdf-form-enrichment-tool

# 2. Run scripts in order
python scripts/setup_script.py
python scripts/upgrade_to_professional.py  
python scripts/add_comprehensive_docs.py

# 3. Complete environment setup
make setup
source venv/bin/activate  # Mac/Linux
# or: venv\Scripts\activate  # Windows

# 4. Install dependencies
make install-dev

# 5. Start building!
# Follow docs/form_editor_task_list.md
```

## 📖 Detailed Script Documentation

### 1. setup_script.py

**Purpose**: Creates the foundation project structure with essential files.

**What it creates**:
- Basic Python package structure
- Essential configuration files (README, setup.py, requirements.txt)
- Simple CLI interface
- Basic Makefile with common commands
- Git configuration files (.gitignore, LICENSE)

**Usage**:
```bash
python scripts/setup_script.py
```

**Prerequisites**: 
- Git repository initialized
- Python 3.9+ installed

**Output**: Basic project structure ready for development

---

### 2. upgrade_to_professional.py

**Purpose**: Transforms the basic setup into a professional-grade development environment.

**What it adds**:
- **CI/CD Pipeline**: GitHub Actions for automated testing
- **Code Quality Tools**: Black, Flake8, MyPy, Bandit, pre-commit hooks
- **Testing Framework**: Pytest with coverage and performance testing
- **Documentation**: Professional README with badges and comprehensive guides
- **Containerization**: Docker and docker-compose configuration
- **Development Tools**: Advanced Makefile, development dependencies
- **GitHub Templates**: Issue and PR templates for collaboration

**Usage**:
```bash
python scripts/upgrade_to_professional.py
```

**Prerequisites**: 
- Basic setup completed (setup_script.py run)
- GitHub repository created
- Virtual environment recommended

**Output**: Enterprise-ready development environment

---

### 3. add_comprehensive_docs.py

**Purpose**: Adds complete project documentation including development guides and technical specifications.

**What it creates**:
- **docs/form_editor_task_list.md**: Step-by-step development tasks with code examples
- **docs/form_field_editor_prd.md**: Product Requirements Document for core engine  
- **docs/mcp_server_prd.md**: Claude Desktop integration specifications
- **docs/api_reference.md**: Complete API documentation with examples
- **docs/user_guide.md**: Comprehensive user guide with troubleshooting
- **docs/README.md**: Documentation overview and navigation

**Usage**:
```bash
python scripts/add_comprehensive_docs.py
```

**Prerequisites**: 
- Project structure in place
- Git repository initialized

**Output**: Complete documentation suite for development and usage

## 🎯 Usage Scenarios

### Scenario 1: Complete Fresh Setup
```bash
# Start from empty GitHub repository
python scripts/setup_script.py           # Basic structure
python scripts/upgrade_to_professional.py # Professional tools  
python scripts/add_comprehensive_docs.py  # Complete documentation
```

### Scenario 2: Learning Path (Recommended for Beginners)
```bash
# Step 1: Start simple
python scripts/setup_script.py
# Explore the files, understand the structure

# Step 2: Add professional tools when ready
python scripts/upgrade_to_professional.py
# Learn about CI/CD, testing, code quality

# Step 3: Get complete documentation
python scripts/add_comprehensive_docs.py
# Start following the development task list
```

### Scenario 3: Documentation Only
```bash
# If you have the code but need docs
python scripts/add_comprehensive_docs.py
```

## 🔧 Script Requirements

### System Requirements
- **Python**: 3.9 or higher
- **Git**: For version control
- **Internet**: For downloading dependencies

### Python Dependencies
These scripts use only standard library modules:
- `os`, `sys`, `pathlib` for file operations
- `json` for configuration files
- No external dependencies required

## ⚠️ Important Notes

### Running Scripts Multiple Times
- **Safe to re-run**: All scripts check for existing files and handle overwrites gracefully
- **Backup created**: upgrade_to_professional.py creates backups before overwriting
- **Incremental**: Scripts only add missing files, won't break existing setup

### File Conflicts
If you get file conflicts:
```bash
# Check what's different
git status
git diff

# Commit your changes first
git add .
git commit -m "Save current work before running script"

# Then run the script
python scripts/script_name.py
```

### Permissions
Scripts create files with standard permissions. If you encounter permission errors:
```bash
# Make script executable (if needed)
chmod +x scripts/*.py

# Run with Python explicitly
python scripts/script_name.py
```

## 🐛 Troubleshooting

### Common Issues

**"No such file or directory"**
- Make sure you're in the project root directory
- Check that `.git` folder exists (indicates Git repository)

**"Permission denied"**
- Ensure you have write permissions to the directory
- Try running with appropriate permissions

**"Module not found"**
- Scripts use only standard library, no additional installs needed
- Ensure Python 3.9+ is being used

**"Git repository required"**
- Scripts expect to run in a Git repository
- Initialize with: `git init` or clone from GitHub

### Getting Help

1. **Check the logs**: Scripts print detailed status messages
2. **Run with Python explicitly**: `python scripts/script_name.py`
3. **Verify prerequisites**: Ensure Git repo and Python version
4. **Check file permissions**: Ensure write access to project directory

## 🎉 What You Get

After running all scripts, your project will have:

✅ **Professional Structure**: Organized, scalable codebase  
✅ **Development Tools**: Everything needed for quality development  
✅ **CI/CD Pipeline**: Automated testing and deployment  
✅ **Complete Documentation**: Guides for development and usage  
✅ **Team Collaboration**: GitHub templates and workflows  
✅ **Quality Assurance**: Testing, linting, and security scanning  
✅ **Containerization**: Docker setup for deployment  
✅ **Task Guidance**: Step-by-step development instructions  

## 🚀 Next Steps

After running the setup scripts:

1. **Set up your environment**:
   ```bash
   make setup
   source venv/bin/activate
   make install-dev
   ```

2. **Configure your API keys**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Start developing**:
   ```bash
   # Read the task list
   cat docs/form_editor_task_list.md
   
   # Start with Task 1.2: Basic PDF Reading
   # Follow the step-by-step instructions
   ```

4. **Test your setup**:
   ```bash
   python -m pdf_form_editor info
   make test
   ```

## 📞 Support

- **Documentation**: Check the `docs/` directory for comprehensive guides
- **Issues**: Open a GitHub issue for bugs or questions  
- **Task Lists**: Follow `docs/form_editor_task_list.md` for development guidance
- **API Reference**: See `docs/api_reference.md` for technical details

---

**Ready to build your PDF processing superpower? Start with the setup scripts and transform your forms workflow! 🚀📄✨**
