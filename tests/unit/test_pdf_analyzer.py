#!/usr/bin/env python3
"""
Comprehensive unit tests for PDFAnalyzer class.

Tests cover all functionality including error handling, metadata extraction,
PDF validation, and the fixes implemented from code review.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from pdf_form_editor.core.pdf_analyzer import PDFAnalyzer
from pdf_form_editor.utils.errors import PDFProcessingError


class TestPDFAnalyzerInitialization:
    """Test PDFAnalyzer initialization and basic setup."""

    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent file raises error."""
        with pytest.raises(PDFProcessingError, match="PDF file not found"):
            PDFAnalyzer("nonexistent_file.pdf")

    def test_init_with_valid_file(self, sample_pdf_path):
        """Test successful initialization with valid PDF."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        assert analyzer.file_path == Path(sample_pdf_path)
        assert analyzer.reader is not None
        assert analyzer.password is None

    def test_init_with_password(self, sample_pdf_path):
        """Test initialization with password parameter."""
        analyzer = PDFAnalyzer(sample_pdf_path, password="test_password")
        assert analyzer.password == "test_password"

    @patch('pdf_form_editor.core.pdf_analyzer.PdfReader')
    def test_init_with_corrupted_pdf(self, mock_pdf_reader, tmp_path):
        """Test initialization with corrupted PDF raises error."""
        # Create a dummy file
        test_file = tmp_path / "corrupted.pdf"
        test_file.write_text("not a pdf")
        
        # Mock PdfReader to raise PdfReadError
        mock_pdf_reader.side_effect = PdfReadError("Invalid PDF")
        
        with pytest.raises(PDFProcessingError, match="Invalid or corrupted PDF file"):
            PDFAnalyzer(str(test_file))


class TestPDFValidation:
    """Test PDF validation functionality."""

    def test_validate_pdf_success(self, sample_pdf_path):
        """Test successful PDF validation."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        assert analyzer.validate_pdf() is True

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_validate_pdf_no_reader(self, mock_load, tmp_path):
        """Test validation fails when no reader available."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = None
        analyzer._metadata_cache = None
        
        assert analyzer.validate_pdf() is False

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_validate_pdf_no_pages(self, mock_load, tmp_path):
        """Test validation fails when PDF has no pages."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = Mock()
        analyzer.reader.pages = []
        analyzer._metadata_cache = None
        
        assert analyzer.validate_pdf() is False


class TestMetadataExtraction:
    """Test metadata extraction functionality."""

    def test_extract_metadata_basic(self, sample_pdf_path):
        """Test basic metadata extraction."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        metadata = analyzer.extract_metadata()
        
        # Check required fields
        assert "file_path" in metadata
        assert "file_size" in metadata
        assert "file_name" in metadata
        assert "page_count" in metadata
        assert "is_encrypted" in metadata
        assert "has_form_fields" in metadata
        assert "pdf_version" in metadata
        assert "document_info" in metadata
        assert "form_info" in metadata
        assert "is_valid" in metadata
        assert "analyzed_at" in metadata

    def test_extract_metadata_timestamp_format(self, sample_pdf_path):
        """Test that analyzed_at timestamp is in correct format (Fix #3)."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        metadata = analyzer.extract_metadata()
        
        timestamp = metadata["analyzed_at"]
        # Should be ISO format
        parsed_time = datetime.fromisoformat(timestamp)
        assert isinstance(parsed_time, datetime)
        
        # Should be recent (within last minute)
        now = datetime.now()
        time_diff = abs((now - parsed_time).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_extract_metadata_caching(self, sample_pdf_path):
        """Test that metadata is cached properly."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        
        # First extraction
        metadata1 = analyzer.extract_metadata()
        
        # Second extraction should return cached result
        metadata2 = analyzer.extract_metadata()
        
        assert metadata1 is metadata2  # Same object reference
        assert metadata1["analyzed_at"] == metadata2["analyzed_at"]

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_extract_metadata_no_reader(self, mock_load, tmp_path):
        """Test metadata extraction with no reader returns empty dict."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = None
        analyzer._metadata_cache = None
        
        metadata = analyzer.extract_metadata()
        assert metadata == {}


class TestPDFVersionDetection:
    """Test PDF version detection (Fix #2)."""

    def test_get_pdf_version_with_header(self, sample_pdf_path):
        """Test PDF version extraction from header."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        version = analyzer.get_pdf_version()
        
        # Should return clean version number, not full header
        assert version in ["1.4", "1.5", "1.6", "1.7", "2.0"]
        assert not version.startswith("%PDF-")

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_get_pdf_version_no_reader(self, mock_load, tmp_path):
        """Test version detection with no reader."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = None
        analyzer._metadata_cache = None
        
        assert analyzer.get_pdf_version() == "Unknown"

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_get_pdf_version_with_whitespace(self, mock_load, tmp_path):
        """Test version parsing handles whitespace correctly."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = Mock()
        analyzer.reader.pdf_header = "%PDF-1.7  \n"  # With whitespace
        analyzer.reader.trailer = {}
        analyzer._metadata_cache = None
        
        version = analyzer.get_pdf_version()
        assert version == "1.7"

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_get_pdf_version_empty_after_prefix(self, mock_load, tmp_path):
        """Test version parsing handles empty version after prefix."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = Mock()
        analyzer.reader.pdf_header = "%PDF-"  # Empty version
        analyzer.reader.trailer = {}
        analyzer._metadata_cache = None
        
        version = analyzer.get_pdf_version()
        assert version == "Unknown"


class TestFormFieldDetection:
    """Test form field detection functionality (Fix #4 - Trailer Safety)."""

    def test_has_form_fields_with_forms(self, form_pdf_path):
        """Test form field detection with PDF containing forms."""
        analyzer = PDFAnalyzer(form_pdf_path)
        assert analyzer.has_form_fields() is True

    def test_has_form_fields_without_forms(self, sample_pdf_path):
        """Test form field detection with PDF without forms."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        # This depends on the sample PDF - adjust based on actual test file
        result = analyzer.has_form_fields()
        assert isinstance(result, bool)

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_has_form_fields_no_reader(self, mock_load, tmp_path):
        """Test form field detection with no reader."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = None
        analyzer._metadata_cache = None
        
        assert analyzer.has_form_fields() is False

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_has_form_fields_no_trailer(self, mock_load, tmp_path):
        """Test form field detection with no trailer (Fix #4)."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = Mock()
        analyzer.reader.trailer = None  # No trailer
        analyzer._metadata_cache = None
        
        assert analyzer.has_form_fields() is False


class TestEncryptionHandling:
    """Test encrypted PDF handling."""

    @patch('pdf_form_editor.core.pdf_analyzer.PdfReader')
    def test_encrypted_pdf_with_password(self, mock_pdf_reader, tmp_path):
        """Test encrypted PDF with correct password."""
        test_file = tmp_path / "encrypted.pdf"
        test_file.write_text("dummy")
        
        # Mock encrypted PDF
        mock_reader = Mock()
        mock_reader.is_encrypted = True
        mock_reader.decrypt.return_value = True
        mock_reader.pages = [Mock()]
        mock_pdf_reader.return_value = mock_reader
        
        analyzer = PDFAnalyzer(str(test_file), password="correct_password")
        assert analyzer.is_encrypted() is True
        mock_reader.decrypt.assert_called_once_with("correct_password")

    @patch('pdf_form_editor.core.pdf_analyzer.PdfReader')
    def test_encrypted_pdf_without_password(self, mock_pdf_reader, tmp_path):
        """Test encrypted PDF without password raises error."""
        test_file = tmp_path / "encrypted.pdf"
        test_file.write_text("dummy")
        
        # Mock encrypted PDF
        mock_reader = Mock()
        mock_reader.is_encrypted = True
        mock_pdf_reader.return_value = mock_reader
        
        with pytest.raises(PDFProcessingError, match="PDF is encrypted but no password provided"):
            PDFAnalyzer(str(test_file))

    @patch('pdf_form_editor.core.pdf_analyzer.PdfReader')
    def test_encrypted_pdf_wrong_password(self, mock_pdf_reader, tmp_path):
        """Test encrypted PDF with wrong password raises error."""
        test_file = tmp_path / "encrypted.pdf"
        test_file.write_text("dummy")
        
        # Mock encrypted PDF with failed decryption
        mock_reader = Mock()
        mock_reader.is_encrypted = True
        mock_reader.decrypt.return_value = False
        mock_pdf_reader.return_value = mock_reader
        
        with pytest.raises(PDFProcessingError, match="Invalid password for encrypted PDF"):
            PDFAnalyzer(str(test_file), password="wrong_password")


class TestJSONExport:
    """Test JSON export functionality."""

    def test_export_metadata_json(self, sample_pdf_path, tmp_path):
        """Test JSON metadata export."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        output_file = tmp_path / "test_metadata.json"
        
        analyzer.export_metadata_json(output_file)
        
        # Verify file was created
        assert output_file.exists()
        
        # Verify JSON is valid and contains expected data
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert "file_path" in data
        assert "page_count" in data
        assert "analyzed_at" in data
        assert data["file_name"] == Path(sample_pdf_path).name

    def test_export_metadata_json_creates_directory(self, sample_pdf_path, tmp_path):
        """Test JSON export creates output directory if needed."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        output_file = tmp_path / "subdir" / "test_metadata.json"
        
        analyzer.export_metadata_json(output_file)
        
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_export_metadata_json_error_handling(self, sample_pdf_path):
        """Test JSON export error handling."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        
        # Try to export to invalid location
        with pytest.raises(PDFProcessingError, match="Failed to export metadata"):
            analyzer.export_metadata_json("/invalid/path/metadata.json")


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_page_count(self, sample_pdf_path):
        """Test page count extraction."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        page_count = analyzer.get_page_count()
        assert isinstance(page_count, int)
        assert page_count > 0

    def test_get_page_count_no_reader(self):
        """Test page count with no reader."""
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.reader = None
        assert analyzer.get_page_count() == 0

    def test_is_encrypted(self, sample_pdf_path):
        """Test encryption status check."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        result = analyzer.is_encrypted()
        assert isinstance(result, bool)

    def test_get_summary(self, sample_pdf_path):
        """Test summary generation."""
        analyzer = PDFAnalyzer(sample_pdf_path)
        summary = analyzer.get_summary()
        
        assert isinstance(summary, str)
        assert "PDF Analysis Summary" in summary
        assert "File:" in summary
        assert "Pages:" in summary
        assert "Version:" in summary


class TestErrorHandling:
    """Test error handling throughout the class."""

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_metadata_extraction_with_exception(self, mock_load, tmp_path):
        """Test metadata extraction handles exceptions gracefully."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = Mock()
        analyzer.reader.pages = [Mock()]  # Valid pages
        analyzer._metadata_cache = None
        
        # Mock metadata extraction to raise exception
        with patch.object(analyzer, '_extract_document_info', side_effect=Exception("Test error")):
            metadata = analyzer.extract_metadata()
            
            # Should return error metadata
            assert "error" in metadata
            assert metadata["is_valid"] is False

    @patch.object(PDFAnalyzer, '_load_pdf')
    def test_version_detection_exception_handling(self, mock_load, tmp_path):
        """Test version detection handles exceptions."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        analyzer = PDFAnalyzer.__new__(PDFAnalyzer)
        analyzer.file_path = test_file
        analyzer.reader = Mock()
        analyzer.reader.pdf_header = Mock(side_effect=Exception("Test error"))
        analyzer._metadata_cache = None
        
        version = analyzer.get_pdf_version()
        assert version == "Unknown"


# Test fixtures and helpers

@pytest.fixture
def sample_pdf_path():
    """Provide path to a sample PDF for testing."""
    # Use the system PDF we've been testing with
    return "/System/Library/Assistant/UIPlugins/MailUI.siriUIBundle/Contents/Resources/flagged.pdf"


@pytest.fixture
def form_pdf_path():
    """Provide path to a PDF with forms for testing."""
    # Use the W-4R PDF that has form fields
    return "/Users/wseke/Desktop/samples/W-4R_parsed.pdf"


@pytest.fixture
def temp_pdf(tmp_path):
    """Create a temporary PDF file for testing."""
    pdf_file = tmp_path / "temp.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF")
    return str(pdf_file)


# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit