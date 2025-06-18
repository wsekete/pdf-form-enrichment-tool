#!/usr/bin/env python3
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
