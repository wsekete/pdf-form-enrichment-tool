"""
Unit tests for BEM name generation system.

Tests the core BEMNameGenerator, PatternLearner, RuleBasedEngine, and BEMNameValidator.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest

from pdf_form_editor.core.field_extractor import FormField, FieldContext
from pdf_form_editor.training.pattern_analyzer import PatternDatabase, ContextPattern, SpatialPattern
from pdf_form_editor.training.similarity_matcher import SimilarityMatcher, SimilarMatch
from pdf_form_editor.naming.bem_generator import (
    BEMNameGenerator, BEMResult, BEMCandidate, GenerationMethod
)
from pdf_form_editor.naming.pattern_learner import PatternLearner, SpatialSuggestion, HierarchySuggestion
from pdf_form_editor.naming.rule_engine import RuleBasedEngine, SemanticCategory, SemanticAnalysis
from pdf_form_editor.naming.name_validator import (
    BEMNameValidator, ValidationResult, UniquenessResult, ValidationSeverity
)


class TestBEMNameGenerator(unittest.TestCase):
    """Test the main BEM name generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock pattern database
        self.mock_pattern_db = PatternDatabase()
        
        # Create sample context patterns
        self.mock_pattern_db.context_patterns = [
            ContextPattern(
                trigger_text=['name', 'owner'],
                bem_block='owner-information',
                bem_element='name',
                confidence=0.9,
                examples=['owner-information_name__first']
            ),
            ContextPattern(
                trigger_text=['phone', 'contact'],
                bem_block='contact-information',
                bem_element='phone',
                confidence=0.8,
                examples=['contact-information_phone__primary']
            )
        ]
        
        # Create mock similarity matcher
        self.mock_similarity_matcher = Mock(spec=SimilarityMatcher)
        
        # Initialize generator
        self.generator = BEMNameGenerator(self.mock_pattern_db, self.mock_similarity_matcher)
    
    def test_initialization(self):
        """Test generator initialization."""
        self.assertIsInstance(self.generator, BEMNameGenerator)
        self.assertEqual(self.generator.patterns, self.mock_pattern_db)
        self.assertEqual(self.generator.matcher, self.mock_similarity_matcher)
        self.assertEqual(len(self.generator.generated_names), 0)
    
    def test_generate_bem_name_exact_match(self):
        """Test BEM name generation with exact pattern match."""
        # Create test field and context
        field = FormField(
            id='field_001',
            name='OwnerName',
            field_type='text',
            page=1,
            rect=[100, 200, 250, 220],
            value='',
            properties={'required': True}
        )
        
        context = FieldContext(
            field_id='field_001',
            label='Owner Name',
            nearby_text=['owner', 'information', 'name'],
            section_header='Owner Information',
            confidence=0.9
        )
        
        # Generate BEM name
        result = self.generator.generate_bem_name(field, context)
        
        # Verify result
        self.assertIsInstance(result, BEMResult)
        self.assertTrue(result.bem_name)
        self.assertGreater(result.confidence, 0.0)
        self.assertEqual(result.field_id, 'field_001')
        self.assertIn('owner-information', result.bem_name)
    
    def test_generate_bem_name_similar_context(self):
        """Test BEM name generation with similar context adaptation."""
        # Mock similarity matcher to return similar matches
        similar_match = SimilarMatch(
            training_example=Mock(),
            similarity_score=0.7,
            matching_factors=['label similarity'],
            recommended_bem='owner-information_address',
            confidence=0.75
        )
        
        self.mock_similarity_matcher.find_similar_contexts.return_value = [similar_match]
        
        field = FormField(
            field_id='field_002',
            field_name='CustomerAddress',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 250, 'width': 200, 'height': 20},
            properties={},
            value=''
        )
        
        context = FieldContext(
            field_id='field_002',
            label_text='Customer Address',
            nearby_text=['customer', 'address', 'street'],
            section_header='Customer Information',
            confidence=0.6
        )
        
        result = self.generator.generate_bem_name(field, context)
        
        # Verify result uses adaptation
        self.assertIsInstance(result, BEMResult)
        self.assertTrue(result.bem_name)
        self.assertIn('address', result.bem_name.lower())
    
    def test_generate_bem_name_fallback(self):
        """Test BEM name generation fallback when no patterns match."""
        # Clear patterns to force fallback
        self.generator.patterns.context_patterns = []
        self.mock_similarity_matcher.find_similar_contexts.return_value = []
        
        field = FormField(
            field_id='field_003',
            field_name='UnknownField',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 300, 'width': 100, 'height': 20},
            properties={},
            value=''
        )
        
        context = FieldContext(
            field_id='field_003',
            label_text='Unknown Field',
            nearby_text=[],
            section_header='',
            confidence=0.1
        )
        
        result = self.generator.generate_bem_name(field, context)
        
        # Verify fallback result
        self.assertIsInstance(result, BEMResult)
        self.assertTrue(result.bem_name)
        self.assertGreater(len(result.bem_name), 3)
    
    def test_uniqueness_enforcement(self):
        """Test that generated names are unique."""
        field1 = FormField(
            field_id='field_001',
            field_name='Name1',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 200, 'width': 150, 'height': 20},
            properties={},
            value=''
        )
        
        field2 = FormField(
            field_id='field_002',
            field_name='Name2',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 250, 'width': 150, 'height': 20},
            properties={},
            value=''
        )
        
        context = FieldContext(
            field_id='field_001',
            label_text='Name',
            nearby_text=['owner', 'name'],
            section_header='Owner Information',
            confidence=0.9
        )
        
        # Generate first name
        result1 = self.generator.generate_bem_name(field1, context)
        
        # Generate second name with same context
        context.field_id = 'field_002'
        result2 = self.generator.generate_bem_name(field2, context)
        
        # Verify names are different
        self.assertNotEqual(result1.bem_name, result2.bem_name)
    
    def test_bem_syntax_validation(self):
        """Test BEM syntax validation."""
        # Valid BEM names
        valid_names = [
            'owner-information_name',
            'contact-information_phone__primary',
            'payment_amount__gross'
        ]
        
        for name in valid_names:
            self.assertTrue(self.generator._validate_bem_syntax(name),
                          f"'{name}' should be valid BEM syntax")
        
        # Invalid BEM names
        invalid_names = [
            'Owner-Information_name',  # Capital letters
            'owner_information_name_extra',  # Too many underscores
            '123-invalid',  # Starts with number
            'owner--information',  # Double hyphens in wrong place
            ''  # Empty string
        ]
        
        for name in invalid_names:
            self.assertFalse(self.generator._validate_bem_syntax(name),
                           f"'{name}' should be invalid BEM syntax")


class TestPatternLearner(unittest.TestCase):
    """Test the pattern learning engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pattern_db = PatternDatabase()
        self.pattern_db.context_patterns = [
            ContextPattern(
                trigger_text=['name', 'first'],
                bem_block='owner-information',
                bem_element='name',
                confidence=0.9,
                examples=['owner-information_name__first']
            )
        ]
        
        self.learner = PatternLearner(self.pattern_db)
    
    def test_apply_context_patterns(self):
        """Test applying context patterns to generate candidates."""
        context = FieldContext(
            field_id='field_001',
            label_text='First Name',
            nearby_text=['owner', 'first', 'name'],
            section_header='Owner Information',
            confidence=0.8
        )
        
        candidates = self.learner.apply_context_patterns(context)
        
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0)
        
        # Check first candidate
        first_candidate = candidates[0]
        self.assertIn('bem_block', first_candidate)
        self.assertIn('bem_element', first_candidate)
        self.assertIn('confidence', first_candidate)
        self.assertGreater(first_candidate['confidence'], 0)
    
    def test_apply_spatial_patterns(self):
        """Test spatial pattern application."""
        field = FormField(
            field_id='field_001',
            field_name='TestField',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 200, 'width': 150, 'height': 20},
            properties={},
            value=''
        )
        
        all_fields = [field]
        
        suggestion = self.learner.apply_spatial_patterns(field, all_fields)
        
        self.assertIsInstance(suggestion, SpatialSuggestion)
        self.assertTrue(suggestion.suggested_block)
        self.assertGreater(suggestion.confidence, 0)
        self.assertGreaterEqual(suggestion.element_sequence, 1)
    
    def test_learn_from_feedback(self):
        """Test learning from user feedback."""
        field = FormField(
            field_id='field_001',
            field_name='UserName',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 200, 'width': 150, 'height': 20},
            properties={},
            value=''
        )
        
        # Record feedback
        initial_feedback_count = len(self.learner.feedback_history)
        self.learner.learn_from_feedback(field, 'owner-information_name__approved', 0.95)
        
        # Verify feedback was recorded
        self.assertEqual(len(self.learner.feedback_history), initial_feedback_count + 1)
        
        latest_feedback = self.learner.feedback_history[-1]
        self.assertEqual(latest_feedback['field_id'], 'field_001')
        self.assertEqual(latest_feedback['chosen_bem_name'], 'owner-information_name__approved')
        self.assertEqual(latest_feedback['confidence'], 0.95)


class TestRuleBasedEngine(unittest.TestCase):
    """Test the rule-based fallback engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = RuleBasedEngine()
    
    def test_semantic_analysis_personal_info(self):
        """Test semantic analysis for personal information fields."""
        context = FieldContext(
            field_id='field_001',
            label_text='First Name',
            nearby_text=['owner', 'personal', 'first', 'name'],
            section_header='Personal Information',
            confidence=0.8
        )
        
        analysis = self.engine.analyze_field_semantics(context)
        
        self.assertIsInstance(analysis, SemanticAnalysis)
        self.assertEqual(analysis.primary_category, SemanticCategory.PERSONAL_INFO)
        self.assertIn('name', analysis.secondary_category)
        self.assertGreater(analysis.confidence, 0)
        self.assertGreater(len(analysis.supporting_evidence), 0)
    
    def test_semantic_analysis_contact_info(self):
        """Test semantic analysis for contact information fields."""
        context = FieldContext(
            field_id='field_002',
            label_text='Phone Number',
            nearby_text=['contact', 'phone', 'telephone', 'number'],
            section_header='Contact Information',
            confidence=0.8
        )
        
        analysis = self.engine.analyze_field_semantics(context)
        
        self.assertEqual(analysis.primary_category, SemanticCategory.CONTACT_INFO)
        self.assertIn('phone', analysis.secondary_category)
    
    def test_semantic_analysis_financial(self):
        """Test semantic analysis for financial fields."""
        context = FieldContext(
            field_id='field_003',
            label_text='Premium Amount',
            nearby_text=['payment', 'premium', 'amount', 'dollar'],
            section_header='Payment Information',
            confidence=0.8
        )
        
        analysis = self.engine.analyze_field_semantics(context)
        
        self.assertEqual(analysis.primary_category, SemanticCategory.FINANCIAL)
        self.assertIn('premium', analysis.secondary_category)
    
    def test_generate_fallback_name(self):
        """Test fallback BEM name generation."""
        field = FormField(
            field_id='field_001',
            field_name='SignatureField',
            field_type='signature',
            page=1,
            coordinates={'x': 100, 'y': 500, 'width': 200, 'height': 50},
            properties={},
            value=''
        )
        
        context = FieldContext(
            field_id='field_001',
            label_text='Owner Signature',
            nearby_text=['signature', 'sign', 'owner'],
            section_header='Signatures',
            confidence=0.7
        )
        
        result = self.engine.generate_fallback_name(field, context)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.bem_name)
        self.assertGreater(result.confidence, 0)
        self.assertIn('signature', result.bem_name.lower())
    
    def test_apply_naming_rules(self):
        """Test application of naming rules."""
        analysis = SemanticAnalysis(
            primary_category=SemanticCategory.PERSONAL_INFO,
            secondary_category='name',
            confidence=0.8,
            supporting_evidence=['keyword: name']
        )
        
        field = FormField(
            field_id='field_001',
            field_name='NameField',
            field_type='text',
            page=1,
            coordinates={'x': 100, 'y': 200, 'width': 150, 'height': 20},
            properties={'required': True},
            value=''
        )
        
        bem_name = self.engine.apply_naming_rules(analysis, field)
        
        self.assertTrue(bem_name)
        self.assertIn('owner-information', bem_name)
        self.assertIn('name', bem_name)


class TestBEMNameValidator(unittest.TestCase):
    """Test the BEM name validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = BEMNameValidator()
    
    def test_validate_bem_syntax_valid_names(self):
        """Test validation of valid BEM names."""
        valid_names = [
            'owner-information_name',
            'contact-information_phone__primary',
            'payment_amount__gross',
            'signatures_owner',
            'general_field'
        ]
        
        for name in valid_names:
            result = self.validator.validate_bem_syntax(name)
            self.assertTrue(result.is_valid, f"'{name}' should be valid")
            self.assertEqual(len(result.errors), 0, f"'{name}' should have no errors")
    
    def test_validate_bem_syntax_invalid_names(self):
        """Test validation of invalid BEM names."""
        invalid_names = [
            'Owner-Information_name',  # Capital letters
            'owner_information_name_extra_parts',  # Too complex
            '123-invalid',  # Starts with number
            'owner--information',  # Double hyphens
            '',  # Empty
            'a',  # Too short
            'owner@information_name'  # Invalid characters
        ]
        
        for name in invalid_names:
            result = self.validator.validate_bem_syntax(name)
            self.assertFalse(result.is_valid, f"'{name}' should be invalid")
            self.assertGreater(len(result.errors), 0, f"'{name}' should have errors")
    
    def test_check_uniqueness(self):
        """Test uniqueness checking."""
        existing_names = ['owner-information_name', 'contact-information_phone']
        
        # Test unique name
        result = self.validator.check_uniqueness('payment_amount', existing_names)
        self.assertTrue(result.is_unique)
        self.assertEqual(len(result.conflicts), 0)
        
        # Test duplicate name
        result = self.validator.check_uniqueness('owner-information_name', existing_names)
        self.assertFalse(result.is_unique)
        self.assertEqual(len(result.conflicts), 1)
        self.assertGreater(len(result.suggested_alternatives), 0)
    
    def test_suggest_alternatives(self):
        """Test alternative name generation."""
        base_name = 'owner-information_name'
        existing_names = ['owner-information_name', 'owner-information_name__2']
        
        alternatives = self.validator.suggest_alternatives(base_name, existing_names)
        
        self.assertIsInstance(alternatives, list)
        self.assertGreater(len(alternatives), 0)
        
        # Verify alternatives are unique
        for alt in alternatives:
            self.assertNotIn(alt, existing_names)
            # Verify alternatives are valid BEM syntax
            result = self.validator.validate_bem_syntax(alt)
            self.assertTrue(result.is_valid, f"Alternative '{alt}' should be valid")
    
    def test_validate_batch(self):
        """Test batch validation."""
        names = [
            'owner-information_name',
            'contact-information_phone__primary',
            'invalid-NAME',  # Invalid case
            'payment_amount',
            'owner-information_name'  # Duplicate
        ]
        
        results = self.validator.validate_batch(names)
        
        self.assertEqual(len(results), len(names))
        
        # Check individual results
        self.assertTrue(results['owner-information_name'].is_valid)
        self.assertTrue(results['contact-information_phone__primary'].is_valid)
        self.assertFalse(results['invalid-NAME'].is_valid)
        self.assertTrue(results['payment_amount'].is_valid)
        
        # The second occurrence of duplicate should be invalid
        duplicate_results = [r for name, r in results.items() 
                           if name == 'owner-information_name']
        # At least one should be marked as duplicate
        self.assertTrue(any('Duplicate' in str(r.errors) for r in duplicate_results))
    
    def test_get_validation_summary(self):
        """Test validation summary generation."""
        names = [
            'valid-name_element',
            'another-valid_name__modifier',
            'Invalid-Name',
            'valid-simple'
        ]
        
        results = self.validator.validate_batch(names)
        summary = self.validator.get_validation_summary(results)
        
        self.assertEqual(summary['total_names'], 4)
        self.assertGreaterEqual(summary['valid_names'], 2)  # At least 2 should be valid
        self.assertGreaterEqual(summary['success_rate'], 0.5)
        self.assertIn('total_errors', summary)
        self.assertIn('total_warnings', summary)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)