"""
Simple unit tests for BEM name generation system.

Tests the core functionality without complex mocking.
"""

import unittest
from unittest.mock import Mock

from pdf_form_editor.core.field_extractor import FormField, FieldContext
from pdf_form_editor.training.pattern_analyzer import PatternDatabase, ContextPattern
from pdf_form_editor.training.similarity_matcher import SimilarityMatcher
from pdf_form_editor.naming.bem_generator import BEMNameGenerator
from pdf_form_editor.naming.rule_engine import RuleBasedEngine
from pdf_form_editor.naming.name_validator import BEMNameValidator


class TestBEMGeneratorSimple(unittest.TestCase):
    """Simple tests for BEM name generator."""
    
    def setUp(self):
        """Set up simple test fixtures."""
        self.pattern_db = PatternDatabase()
        self.similarity_matcher = Mock(spec=SimilarityMatcher)
        self.similarity_matcher.find_similar_contexts.return_value = []
        
        self.generator = BEMNameGenerator(self.pattern_db, self.similarity_matcher)
        self.validator = BEMNameValidator()
    
    def test_simple_bem_generation(self):
        """Test basic BEM name generation."""
        field = FormField(
            id='field_001',
            name='TestField',
            field_type='text',
            page=1,
            rect=[100, 200, 250, 220],
            value='',
            properties={}
        )
        
        context = FieldContext(
            field_id='field_001',
            label='Test Field',
            nearby_text=['test', 'field'],
            section_header='Test Section',
            confidence=0.7
        )
        
        result = self.generator.generate_bem_name(field, context)
        
        # Should generate some BEM name
        self.assertIsNotNone(result.bem_name)
        self.assertGreater(len(result.bem_name), 3)
        
        # Should be valid BEM syntax
        validation = self.validator.validate_bem_syntax(result.bem_name)
        self.assertTrue(validation.is_valid, f"Generated name '{result.bem_name}' should be valid")
    
    def test_bem_syntax_validation(self):
        """Test BEM syntax validation."""
        # Valid names
        valid_names = [
            'owner-information_name',
            'contact_phone',
            'payment_amount__gross'
        ]
        
        for name in valid_names:
            result = self.validator.validate_bem_syntax(name)
            self.assertTrue(result.is_valid, f"'{name}' should be valid")
        
        # Invalid names
        invalid_names = [
            'Owner-Information',  # Capital letters
            '123-invalid',  # Starts with number
            'owner--double-hyphen',  # Double hyphens
            '',  # Empty
            'a'  # Too short
        ]
        
        for name in invalid_names:
            result = self.validator.validate_bem_syntax(name)
            self.assertFalse(result.is_valid, f"'{name}' should be invalid")
    
    def test_uniqueness_checking(self):
        """Test uniqueness checking."""
        existing_names = ['owner-information_name', 'contact_phone']
        
        # Test unique name
        result = self.validator.check_uniqueness('payment_amount', existing_names)
        self.assertTrue(result.is_unique)
        
        # Test duplicate name
        result = self.validator.check_uniqueness('owner-information_name', existing_names)
        self.assertFalse(result.is_unique)
        self.assertGreater(len(result.suggested_alternatives), 0)
    
    def test_rule_based_fallback(self):
        """Test rule-based name generation."""
        engine = RuleBasedEngine()
        
        field = FormField(
            id='field_001',
            name='SignatureField',
            field_type='signature',
            page=1,
            rect=[100, 500, 300, 550],
            value='',
            properties={}
        )
        
        context = FieldContext(
            field_id='field_001',
            label='Owner Signature',
            nearby_text=['signature', 'owner'],
            section_header='Signatures',
            confidence=0.8
        )
        
        result = engine.generate_fallback_name(field, context)
        
        self.assertIsNotNone(result)
        self.assertIn('signature', result.bem_name.lower())
        self.assertGreater(result.confidence, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)