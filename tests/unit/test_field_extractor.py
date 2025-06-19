#!/usr/bin/env python3
"""
Simplified unit tests for FieldExtractor and FormField classes.

Uses mocks to avoid complex PDF object creation.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from pdf_form_editor.core.field_extractor import FieldExtractor, FormField
from pdf_form_editor.core.pdf_analyzer import PDFAnalyzer
from pdf_form_editor.utils.errors import PDFProcessingError


class TestFormField:
    """Test cases for FormField data class."""
    
    def test_form_field_creation(self):
        """Test basic FormField creation."""
        field = FormField(
            id="field_001",
            name="test_field",
            field_type="text",
            page=1,
            rect=[100.0, 200.0, 300.0, 250.0],
            value="test value",
            properties={"required": True}
        )
        
        assert field.id == "field_001"
        assert field.name == "test_field"
        assert field.field_type == "text"
        assert field.page == 1
        assert field.rect == [100.0, 200.0, 300.0, 250.0]
        assert field.value == "test value"
        assert field.properties == {"required": True}
        assert field.width == 200.0
        assert field.height == 50.0
        assert field.is_required is True


class TestFieldExtractor:
    """Test cases for FieldExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_analyzer = Mock(spec=PDFAnalyzer)
        self.mock_reader = Mock()
        self.mock_analyzer.reader = self.mock_reader
        self.mock_analyzer.file_path = Path("test.pdf")
        
    def test_field_extractor_init_valid(self):
        """Test FieldExtractor initialization with valid analyzer."""
        extractor = FieldExtractor(self.mock_analyzer)
        
        assert extractor.pdf_analyzer == self.mock_analyzer
        assert extractor.reader == self.mock_reader
    
    def test_extract_form_fields_no_forms(self):
        """Test extraction when PDF has no form fields."""
        self.mock_analyzer.has_form_fields.return_value = False
        
        extractor = FieldExtractor(self.mock_analyzer)
        fields = extractor.extract_form_fields()
        
        assert fields == []
    
    def test_get_field_name_with_t(self):
        """Test field name extraction using /T."""
        field_obj = Mock()
        field_obj.__contains__ = Mock(side_effect=lambda key: key == "/T")
        field_obj.__getitem__ = Mock(return_value="field_name")
        
        extractor = FieldExtractor(self.mock_analyzer)
        name = extractor._get_field_name(field_obj, 5)
        
        assert name == "field_name"
    
    def test_get_field_name_fallback(self):
        """Test field name fallback when neither /T nor /TU exist."""
        field_obj = Mock()
        field_obj.__contains__ = Mock(return_value=False)
        
        extractor = FieldExtractor(self.mock_analyzer)
        name = extractor._get_field_name(field_obj, 5)
        
        assert name == "Field_5"
    
    def test_determine_field_type_text(self):
        """Test field type determination for text fields."""
        field_obj = Mock()
        field_obj.get = Mock(return_value="/Tx")
        
        extractor = FieldExtractor(self.mock_analyzer)
        field_type = extractor._determine_field_type(field_obj)
        
        assert field_type == "text"
    
    def test_determine_field_type_checkbox(self):
        """Test field type determination for checkbox fields."""
        field_obj = Mock()
        field_obj.get = Mock(side_effect=lambda key, default=None: "/Btn" if key == "/FT" else 0)
        
        extractor = FieldExtractor(self.mock_analyzer)
        field_type = extractor._determine_field_type(field_obj)
        
        assert field_type == "checkbox"
    
    def test_get_field_statistics_empty(self):
        """Test field statistics with no fields."""
        extractor = FieldExtractor(self.mock_analyzer)
        stats = extractor.get_field_statistics([])
        
        assert stats["total_fields"] == 0
        assert stats["field_types"] == {}
        assert stats["pages_with_fields"] == 0
    
    def test_get_field_statistics_with_fields(self):
        """Test field statistics with various field types."""
        fields = [
            FormField("1", "field1", "text", 1, [0, 0, 100, 50], "value1", {"required": True}),
            FormField("2", "field2", "text", 1, [0, 60, 100, 110], "", {"readonly": True}),
            FormField("3", "field3", "checkbox", 2, [0, 0, 20, 20], "", {}),
        ]
        
        extractor = FieldExtractor(self.mock_analyzer)
        stats = extractor.get_field_statistics(fields)
        
        assert stats["total_fields"] == 3
        assert stats["field_types"]["text"] == 2
        assert stats["field_types"]["checkbox"] == 1
        assert stats["pages_with_fields"] == 2
        assert stats["required_fields"] == 1
        assert stats["readonly_fields"] == 1


class TestFieldExtractorIntegration:
    """Integration tests using simplified mocking."""
    
    def test_extract_form_fields_with_mocked_structure(self):
        """Test field extraction with mocked PDF structure."""
        mock_analyzer = Mock(spec=PDFAnalyzer)
        mock_reader = Mock()
        mock_analyzer.reader = mock_reader
        mock_analyzer.file_path = Path("test.pdf")
        mock_analyzer.has_form_fields.return_value = True
        
        # Mock field object with proper spec
        from pypdf.generic import DictionaryObject, IndirectObject
        mock_field = Mock(spec=DictionaryObject)
        mock_field.__contains__ = Mock(return_value=True)
        mock_field.get = Mock(side_effect=lambda key, default=None: {
            "/T": "test_field",
            "/FT": "/Tx",
            "/V": "test_value",
            "/Rect": [100, 200, 300, 250],
            "/Ff": 2
        }.get(key, default))
        mock_field.__getitem__ = Mock(side_effect=lambda key: {
            "/T": "test_field",
            "/FT": "/Tx", 
            "/V": "test_value",
            "/Rect": [100, 200, 300, 250],
            "/Ff": 2
        }[key])
        
        mock_field_ref = Mock(spec=IndirectObject)
        mock_field_ref.get_object.return_value = mock_field
        
        mock_reader.trailer = {
            "/Root": {
                "/AcroForm": {
                    "/Fields": [mock_field_ref]
                }
            }
        }
        
        extractor = FieldExtractor(mock_analyzer)
        
        with patch.object(extractor, '_find_field_page', return_value=1):
            fields = extractor.extract_form_fields()
        
        assert len(fields) == 1
        assert fields[0].name == "test_field"
        assert fields[0].field_type == "text"
        assert fields[0].value == "test_value"
        assert fields[0].is_required is True
    
    def test_radio_group_with_missing_kids(self):
        """Test radio group handling when /Kids array is malformed."""
        mock_analyzer = Mock(spec=PDFAnalyzer)
        mock_reader = Mock()
        mock_analyzer.reader = mock_reader
        mock_analyzer.file_path = Path("test.pdf")
        mock_analyzer.has_form_fields.return_value = True
        
        # Mock field with /Kids but empty array
        from pypdf.generic import DictionaryObject, IndirectObject
        mock_field = Mock(spec=DictionaryObject)
        mock_field.__contains__ = Mock(side_effect=lambda key: key == "/Kids")
        mock_field.get = Mock(side_effect=lambda key, default=None: {
            "/Kids": [],  # Empty kids array
            "/T": "empty_group",
            "/FT": "/Btn",
            "/Ff": 32768  # Radio button flag
        }.get(key, default))
        mock_field.__getitem__ = Mock(side_effect=lambda key: {
            "/Kids": [],
            "/T": "empty_group", 
            "/FT": "/Btn",
            "/Ff": 32768
        }[key])
        
        mock_field_ref = Mock(spec=IndirectObject)
        mock_field_ref.get_object.return_value = mock_field
        
        mock_reader.trailer = {
            "/Root": {
                "/AcroForm": {
                    "/Fields": [mock_field_ref]
                }
            }
        }
        
        extractor = FieldExtractor(mock_analyzer)
        fields = extractor.extract_form_fields()
        
        # Should still extract the parent group even with no children
        # Should still extract the parent group even with no children
        assert len(fields) == 1
        assert fields[0].name == "empty_group"
        assert fields[0].field_type == "radio"
    
    def test_radio_widget_without_export_value(self):
        """Test widget handling when export values are missing."""
        mock_analyzer = Mock(spec=PDFAnalyzer)
        mock_reader = Mock()
        mock_analyzer.reader = mock_reader
        mock_analyzer.file_path = Path("test.pdf")
        mock_analyzer.has_form_fields.return_value = True
        
        # Mock radio group with child that has no export value
        from pypdf.generic import DictionaryObject, IndirectObject
        
        # Child widget without export value
        mock_child = Mock(spec=DictionaryObject)
        mock_child.__contains__ = Mock(return_value=False)  # No /AS, /AP, or /V
        mock_child.get = Mock(side_effect=lambda key, default=None: {
            "/FT": "/Btn",
            "/Rect": [100, 200, 120, 220]
        }.get(key, default))
        
        mock_child_ref = Mock(spec=IndirectObject)
        mock_child_ref.get_object.return_value = mock_child
        
        # Parent group
        mock_parent = Mock(spec=DictionaryObject)
        mock_parent.__contains__ = Mock(side_effect=lambda key: key == "/Kids")
        mock_parent.get = Mock(side_effect=lambda key, default=None: {
            "/Kids": [mock_child_ref],
            "/T": "parent_group",
            "/FT": "/Btn"
        }.get(key, default))
        mock_parent.__getitem__ = Mock(side_effect=lambda key: {
            "/Kids": [mock_child_ref],
            "/T": "parent_group",
            "/FT": "/Btn"
        }[key])
        
        mock_parent_ref = Mock(spec=IndirectObject)
        mock_parent_ref.get_object.return_value = mock_parent
        
        mock_reader.trailer = {
            "/Root": {
                "/AcroForm": {
                    "/Fields": [mock_parent_ref]
                }
            }
        }
        
        extractor = FieldExtractor(mock_analyzer)
        
        with patch.object(extractor, '_find_field_page', return_value=1):
            fields = extractor.extract_form_fields()
        
        # Should extract both parent and child, with fallback naming
        assert len(fields) == 2
        parent_field = next(f for f in fields if f.properties.get("is_group_container", False))
        child_field = next(f for f in fields if not f.properties.get("is_group_container", False))
        
        assert parent_field.name == "parent_group"
        assert child_field.name == "parent_group__option_0"  # Fallback naming
        assert child_field.parent == "parent_group"