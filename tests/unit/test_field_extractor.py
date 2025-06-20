#!/usr/bin/env python3
"""
Simplified unit tests for FieldExtractor and FormField classes.

Uses mocks to avoid complex PDF object creation.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from pdf_form_editor.core.field_extractor import FieldExtractor, FormField, FieldContext, ContextExtractor
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


class TestFieldContext:
    """Test cases for FieldContext data class."""
    
    def test_field_context_creation(self):
        """Test basic FieldContext creation."""
        context = FieldContext(
            field_id="field_001",
            nearby_text=["First Name:", "Enter your first name"],
            section_header="Personal Information",
            label="First Name",
            confidence=0.8,
            visual_group="upper_section",
            text_above="Personal Information",
            text_left="First Name:",
            context_properties={"extraction_method": "proximity_analysis"}
        )
        
        assert context.field_id == "field_001"
        assert len(context.nearby_text) == 2
        assert context.section_header == "Personal Information"
        assert context.label == "First Name"
        assert context.confidence == 0.8
        assert context.visual_group == "upper_section"
        assert context.text_above == "Personal Information"
        assert context.text_left == "First Name:"
        assert context.context_properties["extraction_method"] == "proximity_analysis"
    
    def test_field_context_defaults(self):
        """Test FieldContext with default values."""
        context = FieldContext(field_id="field_002")
        
        assert context.field_id == "field_002"
        assert context.nearby_text == []
        assert context.section_header == ""
        assert context.label == ""
        assert context.confidence == 0.0
        assert context.visual_group == ""
        assert context.text_above == ""
        assert context.text_below == ""
        assert context.text_left == ""
        assert context.text_right == ""
        assert context.context_properties == {}


class TestContextExtractor:
    """Test cases for ContextExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_analyzer = Mock(spec=PDFAnalyzer)
        self.mock_reader = Mock()
        self.mock_analyzer.reader = self.mock_reader
        
        # Mock a page with extract_text method
        self.mock_page = Mock()
        self.mock_page.extract_text.return_value = """
        PERSONAL INFORMATION SECTION
        
        First Name: [text field here]
        Last Name: [text field here]
        
        CONTACT INFORMATION
        
        Email Address: [text field here]
        Phone Number: [text field here]
        """
        
        self.mock_reader.pages = [self.mock_page]
        
        # Sample field for testing
        self.sample_field = FormField(
            id="field_001",
            name="first_name",
            field_type="text",
            page=1,
            rect=[200.0, 600.0, 400.0, 625.0],
            value="",
            properties={}
        )
    
    def test_context_extractor_initialization(self):
        """Test ContextExtractor initialization."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        assert extractor.pdf_analyzer == self.mock_analyzer
        assert extractor.reader == self.mock_reader
        assert extractor._page_texts == {}
        assert extractor._text_elements == {}
    
    def test_get_page_text_caching(self):
        """Test page text extraction with caching."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        # First call should extract text
        text1 = extractor._get_page_text(1)
        assert "PERSONAL INFORMATION" in text1
        assert self.mock_page.extract_text.call_count == 1
        
        # Second call should use cache
        text2 = extractor._get_page_text(1)
        assert text1 == text2
        assert self.mock_page.extract_text.call_count == 1  # Still just one call
    
    def test_get_page_text_invalid_page(self):
        """Test page text extraction for invalid page numbers."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        # Page 0 (invalid)
        text = extractor._get_page_text(0)
        assert text == ""
        
        # Page beyond range
        text = extractor._get_page_text(10)
        assert text == ""
    
    def test_extract_text_elements(self):
        """Test text element extraction with positioning."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        elements = extractor._extract_text_elements(1)
        
        # Should have multiple text elements
        assert len(elements) > 0
        
        # Check element structure
        first_element = elements[0]
        assert 'text' in first_element
        assert 'x' in first_element
        assert 'y' in first_element
        assert 'width' in first_element
        assert 'height' in first_element
        assert 'line_index' in first_element
        
        # Should start from top of page
        assert first_element['y'] == 800
    
    def test_find_nearby_text(self):
        """Test finding text near field coordinates."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        # Create mock text elements
        text_elements = [
            {'text': 'First Name:', 'x': 100, 'y': 600, 'width': 60, 'height': 12},
            {'text': 'Last Name:', 'x': 100, 'y': 580, 'width': 60, 'height': 12},
            {'text': 'PERSONAL INFORMATION', 'x': 100, 'y': 700, 'width': 120, 'height': 12},
            {'text': 'Far away text', 'x': 500, 'y': 200, 'width': 80, 'height': 12},
        ]
        
        field_rect = [200.0, 600.0, 400.0, 625.0]
        nearby_text = extractor._find_nearby_text(text_elements, field_rect)
        
        # Should find nearby text, sorted by relevance
        assert len(nearby_text) > 0
        assert 'First Name:' in nearby_text
        assert 'Far away text' not in nearby_text  # Too far away
    
    def test_detect_field_label(self):
        """Test field label detection."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        # Test with colon-terminated label
        nearby_text = ['First Name:', 'Enter your name', 'Required field']
        label = extractor._detect_field_label(nearby_text, [100, 100, 200, 120])
        assert label == 'First Name'
        
        # Test with field indicator
        nearby_text = ['Enter email address', 'Contact info', 'Optional']
        label = extractor._detect_field_label(nearby_text, [100, 100, 200, 120])
        assert 'email' in label.lower()
        
        # Test with empty nearby text
        label = extractor._detect_field_label([], [100, 100, 200, 120])
        assert label == ""
    
    def test_find_section_header(self):
        """Test section header detection."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        page_text = """
        PERSONAL INFORMATION SECTION
        
        First Name: [field]
        Last Name: [field]
        
        Contact Information:
        Email: [field]
        """
        
        header = extractor._find_section_header(page_text, [100, 100, 200, 120])
        assert 'PERSONAL INFORMATION' in header or 'Contact Information' in header
    
    def test_determine_visual_group(self):
        """Test visual grouping determination."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        # Test different vertical positions
        field_top = FormField("f1", "test", "text", 1, [100, 750, 200, 770], "", {})
        field_middle = FormField("f2", "test", "text", 1, [100, 400, 200, 420], "", {})
        field_bottom = FormField("f3", "test", "text", 1, [100, 50, 200, 70], "", {})
        
        assert extractor._determine_visual_group(field_top, []) == "header_section"
        assert extractor._determine_visual_group(field_middle, []) == "middle_section"
        assert extractor._determine_visual_group(field_bottom, []) == "footer_section"
    
    def test_extract_directional_text(self):
        """Test directional text extraction."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        text_elements = [
            {'text': 'Above text', 'x': 200, 'y': 650, 'width': 60, 'height': 12},
            {'text': 'Below text', 'x': 200, 'y': 580, 'width': 60, 'height': 12},
            {'text': 'Left text', 'x': 50, 'y': 600, 'width': 60, 'height': 12},
            {'text': 'Right text', 'x': 450, 'y': 600, 'width': 60, 'height': 12},
        ]
        
        field_rect = [200.0, 600.0, 400.0, 625.0]
        
        text_above = extractor._extract_directional_text(text_elements, field_rect, "above")
        text_below = extractor._extract_directional_text(text_elements, field_rect, "below")
        text_left = extractor._extract_directional_text(text_elements, field_rect, "left")
        text_right = extractor._extract_directional_text(text_elements, field_rect, "right")
        
        assert text_above == "Above text"
        assert text_below == "Below text"
        assert text_left == "Left text"
        assert text_right == "Right text"
    
    def test_calculate_context_confidence(self):
        """Test context confidence calculation."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        # High confidence case
        confidence = extractor._calculate_context_confidence(
            label="First Name",
            nearby_text=["First Name:", "Enter name", "Required"],
            section_header="Personal Information",
            text_above="Personal Information",
            text_left="First Name:"
        )
        assert confidence > 0.8
        
        # Low confidence case
        confidence = extractor._calculate_context_confidence(
            label="",
            nearby_text=[],
            section_header="",
            text_above="",
            text_left=""
        )
        assert confidence <= 0.5
    
    def test_extract_field_context_complete(self):
        """Test complete field context extraction."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        context = extractor.extract_field_context(self.sample_field)
        
        # Check all expected attributes are present
        assert context.field_id == "field_001"
        assert isinstance(context.nearby_text, list)
        assert isinstance(context.section_header, str)
        assert isinstance(context.label, str)
        assert isinstance(context.confidence, float)
        assert isinstance(context.visual_group, str)
        assert isinstance(context.text_above, str)
        assert isinstance(context.text_below, str)
        assert isinstance(context.text_left, str)
        assert isinstance(context.text_right, str)
        assert isinstance(context.context_properties, dict)
        
        # Check context properties
        assert context.context_properties["field_type"] == "text"
        assert context.context_properties["field_name"] == "first_name"
        assert context.context_properties["page_number"] == 1
        assert context.context_properties["extraction_method"] == "proximity_analysis"
    
    def test_extract_field_context_error_handling(self):
        """Test error handling in context extraction."""
        # Create extractor with invalid analyzer that will cause an error
        broken_analyzer = Mock(spec=PDFAnalyzer)
        broken_analyzer.reader = None
        
        extractor = ContextExtractor(broken_analyzer)
        
        context = extractor.extract_field_context(self.sample_field)
        
        # Should return context with low confidence due to lack of page text
        assert context.field_id == "field_001"
        assert context.confidence <= 0.5  # Low confidence due to missing text
        assert context.nearby_text == []  # No nearby text found
        assert context.section_header == ""  # No section header found
    
    def test_extract_all_contexts(self):
        """Test extracting contexts for multiple fields."""
        extractor = ContextExtractor(self.mock_analyzer)
        
        fields = [
            self.sample_field,
            FormField("field_002", "last_name", "text", 1, [200, 575, 400, 600], "", {})
        ]
        
        contexts = extractor.extract_all_contexts(fields)
        
        assert len(contexts) == 2
        assert "field_001" in contexts
        assert "field_002" in contexts
        assert isinstance(contexts["field_001"], FieldContext)
        assert isinstance(contexts["field_002"], FieldContext)