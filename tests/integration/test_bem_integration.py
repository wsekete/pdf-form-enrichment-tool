"""
Integration tests for BEM name generation system.

Tests the complete workflow from field extraction to BEM name generation.
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from pdf_form_editor.core.pdf_analyzer import PDFAnalyzer
from pdf_form_editor.core.field_extractor import FieldExtractor, FormField, FieldContext
from pdf_form_editor.training.pattern_analyzer import PatternAnalyzer, PatternDatabase
from pdf_form_editor.training.similarity_matcher import SimilarityMatcher
from pdf_form_editor.training.data_loader import TrainingDataLoader
from pdf_form_editor.naming.bem_generator import BEMNameGenerator
from pdf_form_editor.naming.pattern_learner import PatternLearner
from pdf_form_editor.naming.rule_engine import RuleBasedEngine
from pdf_form_editor.naming.name_validator import BEMNameValidator


class TestBEMIntegration(unittest.TestCase):
    """Integration tests for complete BEM generation workflow."""
    
    def setUp(self):
        """Set up integration test environment."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock training data
        self.create_mock_training_data()
        
        # Initialize pattern database
        self.pattern_db = self.create_test_pattern_database()
        
        # Initialize components
        self.similarity_matcher = SimilarityMatcher()
        self.bem_generator = BEMNameGenerator(self.pattern_db, self.similarity_matcher)
        self.pattern_learner = PatternLearner(self.pattern_db)
        self.rule_engine = RuleBasedEngine()
        self.validator = BEMNameValidator()
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_mock_training_data(self):
        """Create mock training data for testing."""
        training_data = {
            "version": "1.0.0",
            "patterns": {
                "owner-information_name": {
                    "frequency": 15,
                    "contexts": ["owner name", "applicant name", "insured name"],
                    "confidence": 0.9
                },
                "contact-information_phone": {
                    "frequency": 12,
                    "contexts": ["phone number", "telephone", "contact phone"],
                    "confidence": 0.85
                },
                "payment_amount": {
                    "frequency": 8,
                    "contexts": ["premium amount", "payment", "dollar amount"],
                    "confidence": 0.8
                }
            }
        }
        
        # Save to temporary file
        training_file = Path(self.temp_dir) / "training_data.json"
        with open(training_file, 'w') as f:
            json.dump(training_data, f)
        
        return str(training_file)
    
    def create_test_pattern_database(self):
        """Create a test pattern database."""
        from pdf_form_editor.training.pattern_analyzer import ContextPattern, SpatialPattern
        
        db = PatternDatabase()
        
        # Add context patterns
        db.context_patterns = [
            ContextPattern(
                trigger_text=['name', 'owner', 'applicant'],
                bem_block='owner-information',
                bem_element='name',
                confidence=0.9,
                examples=['owner-information_name__first', 'owner-information_name__last']
            ),
            ContextPattern(
                trigger_text=['phone', 'telephone', 'contact'],
                bem_block='contact-information',
                bem_element='phone',
                confidence=0.85,
                examples=['contact-information_phone__home', 'contact-information_phone__work']
            ),
            ContextPattern(
                trigger_text=['amount', 'premium', 'payment'],
                bem_block='payment',
                bem_element='amount',
                confidence=0.8,
                examples=['payment_amount__premium', 'payment_amount__total']
            )
        ]
        
        # Add spatial patterns
        db.spatial_patterns = [
            SpatialPattern(
                position_range={'x': (0, 300), 'y': (0, 200), 'width': (0, 200), 'height': (0, 30)},
                typical_block='owner-information',
                field_sequence=['name', 'address', 'phone'],
                confidence=0.75
            )
        ]
        
        return db
    
    def create_test_fields(self):
        """Create test form fields for testing."""
        fields = [
            FormField(
                field_id='field_001',
                field_name='OwnerFirstName',
                field_type='text',
                page=1,
                coordinates={'x': 100, 'y': 50, 'width': 150, 'height': 20},
                properties={'required': True},
                value=''
            ),
            FormField(
                field_id='field_002',
                field_name='OwnerLastName',
                field_type='text',
                page=1,
                coordinates={'x': 100, 'y': 80, 'width': 150, 'height': 20},
                properties={'required': True},
                value=''
            ),
            FormField(
                field_id='field_003',
                field_name='ContactPhone',
                field_type='text',
                page=1,
                coordinates={'x': 100, 'y': 110, 'width': 120, 'height': 20},
                properties={},
                value=''
            ),
            FormField(
                field_id='field_004',
                field_name='PremiumAmount',
                field_type='text',
                page=1,
                coordinates={'x': 100, 'y': 300, 'width': 100, 'height': 20},
                properties={},
                value=''
            )
        ]
        
        return fields
    
    def create_test_contexts(self):
        """Create test field contexts."""
        contexts = [
            FieldContext(
                field_id='field_001',
                label_text='First Name',
                nearby_text=['owner', 'information', 'first', 'name'],
                section_header='Owner Information',
                confidence=0.9
            ),
            FieldContext(
                field_id='field_002',
                label_text='Last Name',
                nearby_text=['owner', 'information', 'last', 'name'],
                section_header='Owner Information',
                confidence=0.9
            ),
            FieldContext(
                field_id='field_003',
                label_text='Phone Number',
                nearby_text=['contact', 'phone', 'number'],
                section_header='Contact Information',
                confidence=0.85
            ),
            FieldContext(
                field_id='field_004',
                label_text='Premium Amount',
                nearby_text=['payment', 'premium', 'amount', 'dollar'],
                section_header='Payment Information',
                confidence=0.8
            )
        ]
        
        return contexts
    
    def test_complete_bem_generation_workflow(self):
        """Test the complete BEM generation workflow."""
        fields = self.create_test_fields()
        contexts = self.create_test_contexts()
        
        # Generate BEM names for all fields
        bem_results = []
        generated_names = []
        
        for field, context in zip(fields, contexts):
            result = self.bem_generator.generate_bem_name(field, context)
            bem_results.append(result)
            generated_names.append(result.bem_name)
        
        # Verify all results
        self.assertEqual(len(bem_results), len(fields))
        
        for i, result in enumerate(bem_results):
            # Check result structure
            self.assertIsNotNone(result.bem_name)
            self.assertGreater(result.confidence, 0)
            self.assertEqual(result.field_id, fields[i].field_id)
            
            # Validate BEM syntax
            validation = self.validator.validate_bem_syntax(result.bem_name)
            self.assertTrue(validation.is_valid, 
                          f"Generated name '{result.bem_name}' should be valid BEM")
        
        # Check uniqueness
        self.assertEqual(len(generated_names), len(set(generated_names)),
                        "All generated names should be unique")
    
    def test_pattern_matching_accuracy(self):
        """Test accuracy of pattern matching."""
        fields = self.create_test_fields()
        contexts = self.create_test_contexts()
        
        # Test specific pattern matches
        name_field = fields[0]  # First name field
        name_context = contexts[0]
        
        result = self.bem_generator.generate_bem_name(name_field, name_context)
        
        # Should match owner-information pattern
        self.assertIn('owner-information', result.bem_name)
        self.assertIn('name', result.bem_name)
        self.assertGreater(result.confidence, 0.7)
    
    def test_spatial_pattern_application(self):
        """Test spatial pattern application."""
        fields = self.create_test_fields()
        
        # Test spatial grouping for fields in same region
        spatial_suggestions = []
        
        for field in fields[:3]:  # First 3 fields are in same spatial region
            suggestion = self.pattern_learner.apply_spatial_patterns(field, fields)
            spatial_suggestions.append(suggestion)
        
        # Verify spatial suggestions
        for suggestion in spatial_suggestions:
            self.assertIsNotNone(suggestion.suggested_block)
            self.assertGreater(suggestion.confidence, 0)
    
    def test_rule_based_fallback(self):
        """Test rule-based fallback for unknown patterns."""
        # Create field with no matching patterns
        unknown_field = FormField(
            field_id='field_999',
            field_name='UnknownField',
            field_type='text',
            page=1,
            coordinates={'x': 500, 'y': 500, 'width': 100, 'height': 20},
            properties={},
            value=''
        )
        
        unknown_context = FieldContext(
            field_id='field_999',
            label_text='Unknown Field',
            nearby_text=['unknown', 'mystery'],
            section_header='Unknown Section',
            confidence=0.1
        )
        
        # Clear pattern database to force rule-based fallback
        empty_db = PatternDatabase()
        empty_generator = BEMNameGenerator(empty_db, self.similarity_matcher)
        
        result = empty_generator.generate_bem_name(unknown_field, unknown_context)
        
        # Should still generate a valid BEM name
        self.assertIsNotNone(result.bem_name)
        validation = self.validator.validate_bem_syntax(result.bem_name)
        self.assertTrue(validation.is_valid)
    
    def test_validation_integration(self):
        """Test integration with validation system."""
        fields = self.create_test_fields()
        contexts = self.create_test_contexts()
        
        # Generate names
        generated_names = []
        for field, context in zip(fields, contexts):
            result = self.bem_generator.generate_bem_name(field, context)
            generated_names.append(result.bem_name)
        
        # Batch validate
        validation_results = self.validator.validate_batch(generated_names)
        
        # Check validation results
        self.assertEqual(len(validation_results), len(generated_names))
        
        valid_count = sum(1 for r in validation_results.values() if r.is_valid)
        self.assertGreater(valid_count, 0, "At least some names should be valid")
        
        # Get summary
        summary = self.validator.get_validation_summary(validation_results)
        self.assertGreaterEqual(summary['success_rate'], 0.5)
    
    def test_learning_and_adaptation(self):
        """Test learning from feedback and pattern adaptation."""
        field = self.create_test_fields()[0]
        context = self.create_test_contexts()[0]
        
        # Generate initial name
        result1 = self.bem_generator.generate_bem_name(field, context)
        initial_name = result1.bem_name
        
        # Provide feedback
        self.pattern_learner.learn_from_feedback(field, initial_name, 0.95)
        
        # Generate name again
        result2 = self.bem_generator.generate_bem_name(field, context)
        
        # Verify feedback was recorded
        self.assertGreater(len(self.pattern_learner.feedback_history), 0)
        
        latest_feedback = self.pattern_learner.feedback_history[-1]
        self.assertEqual(latest_feedback['chosen_bem_name'], initial_name)
        self.assertEqual(latest_feedback['confidence'], 0.95)
    
    def test_error_handling(self):
        """Test error handling in integration scenarios."""
        # Test with invalid field data
        invalid_field = FormField(
            field_id='',  # Empty ID
            field_name='',  # Empty name
            field_type='unknown',  # Unknown type
            page=0,  # Invalid page
            coordinates={},  # Empty coordinates
            properties={},
            value=None
        )
        
        invalid_context = FieldContext(
            field_id='',
            label_text='',
            nearby_text=[],
            section_header='',
            confidence=0.0
        )
        
        # Should still generate a result without crashing
        try:
            result = self.bem_generator.generate_bem_name(invalid_field, invalid_context)
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.bem_name)
        except Exception as e:
            self.fail(f"BEM generation should not crash with invalid input: {e}")
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        import time
        
        # Create larger dataset
        large_fields = []
        large_contexts = []
        
        for i in range(50):  # 50 fields
            field = FormField(
                field_id=f'field_{i:03d}',
                field_name=f'TestField{i}',
                field_type='text',
                page=1,
                coordinates={'x': (i % 10) * 50, 'y': (i // 10) * 30, 'width': 100, 'height': 20},
                properties={},
                value=''
            )
            
            context = FieldContext(
                field_id=f'field_{i:03d}',
                label_text=f'Test Field {i}',
                nearby_text=['test', 'field', str(i)],
                section_header='Test Section',
                confidence=0.7
            )
            
            large_fields.append(field)
            large_contexts.append(context)
        
        # Measure generation time
        start_time = time.time()
        
        results = []
        for field, context in zip(large_fields, large_contexts):
            result = self.bem_generator.generate_bem_name(field, context)
            results.append(result)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Verify all results
        self.assertEqual(len(results), 50)
        
        # Performance should be reasonable (less than 10 seconds for 50 fields)
        self.assertLess(generation_time, 10.0, 
                       f"Generation took too long: {generation_time:.2f}s for 50 fields")
        
        # Verify uniqueness
        generated_names = [r.bem_name for r in results]
        unique_names = set(generated_names)
        uniqueness_rate = len(unique_names) / len(generated_names)
        self.assertGreater(uniqueness_rate, 0.9, "Should maintain high uniqueness rate")


if __name__ == '__main__':
    unittest.main(verbosity=2)