"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_pdf_path():
    """Sample PDF path for testing."""
    return Path("tests/fixtures/sample_form.pdf")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()
    response = Mock()
    response.choices[0].message.content = "owner-information_name__first"
    client.chat.completions.create.return_value = response
    return client
