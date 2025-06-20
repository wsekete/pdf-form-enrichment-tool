"""
Pattern Learning Engine

Learn and apply patterns from training data for BEM generation.
Handles context patterns, spatial patterns, and hierarchy patterns.
"""

from dataclasses import dataclass, field as dataclass_field
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict, Counter
import math

from ..core.field_extractor import FormField, FieldContext
from ..training.pattern_analyzer import PatternDatabase, ContextPattern, SpatialPattern
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SpatialSuggestion:
    """Suggestion based on spatial positioning patterns."""
    suggested_block: str
    visual_group_id: str
    element_sequence: int
    confidence: float
    supporting_patterns: List[str] = dataclass_field(default_factory=list)


@dataclass
class HierarchySuggestion:
    """Suggestion based on field hierarchy patterns."""
    parent_block: str
    element_name: str
    modifier_suggestion: Optional[str]
    inheritance_rules: List[str] = dataclass_field(default_factory=list)
    confidence: float = 0.0


class PatternLearner:
    """Learn and apply patterns from training data for BEM generation."""
    
    def __init__(self, pattern_database: PatternDatabase):
        """Initialize with pattern database."""
        self.patterns = pattern_database
        self.feedback_history = []  # Track user feedback for learning
        
        logger.info(f"PatternLearner initialized with {len(pattern_database.context_patterns)} "
                   f"context patterns and {len(pattern_database.spatial_patterns)} spatial patterns")
    
    def apply_context_patterns(self, context: FieldContext) -> List[Dict[str, Any]]:
        """
        Apply learned context patterns to generate BEM candidates.
        
        Args:
            context: Field context to analyze
            
        Returns:
            List of BEM candidates with confidence scores
        """
        candidates = []
        
        # Combine all context text for analysis
        context_text = self._extract_context_text(context)
        
        for pattern in self.patterns.context_patterns:
            match_score = self._calculate_pattern_match(pattern, context_text, context)
            
            if match_score > 0.3:  # Minimum threshold for consideration
                candidate = {
                    'bem_block': pattern.bem_block,
                    'bem_element': pattern.bem_element,
                    'confidence': match_score * pattern.confidence,
                    'source_pattern': pattern,
                    'matching_triggers': self._find_matching_triggers(pattern, context_text),
                    'spatial_match': self._check_spatial_indicators(pattern, context)
                }
                candidates.append(candidate)
        
        # Sort by confidence
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.debug(f"Applied context patterns: {len(candidates)} candidates generated")
        return candidates[:5]  # Return top 5 candidates
    
    def apply_spatial_patterns(self, field: FormField, all_fields: List[FormField]) -> SpatialSuggestion:
        """
        Apply spatial positioning patterns to suggest BEM structure.
        
        Args:
            field: Current field to analyze
            all_fields: All fields in the document for spatial context
            
        Returns:
            Spatial suggestion with block and sequence information
        """
        field_x = field.coordinates.get('x', 0)
        field_y = field.coordinates.get('y', 0)
        
        best_pattern = None
        best_score = 0.0
        
        for pattern in self.patterns.spatial_patterns:
            score = self._calculate_spatial_match(pattern, field_x, field_y)
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        if best_pattern and best_score > 0.4:
            # Determine element sequence within the spatial group
            sequence = self._calculate_element_sequence(field, all_fields, best_pattern)
            
            suggestion = SpatialSuggestion(
                suggested_block=best_pattern.typical_block,
                visual_group_id=f"spatial_group_{hash(best_pattern) % 1000}",
                element_sequence=sequence,
                confidence=best_score * best_pattern.confidence,
                supporting_patterns=[f"Position: {best_pattern.position_range}"]
            )
            
            logger.debug(f"Applied spatial pattern: block='{suggestion.suggested_block}', "
                        f"sequence={sequence}, confidence={suggestion.confidence:.2f}")
            return suggestion
        
        # Fallback spatial suggestion
        return SpatialSuggestion(
            suggested_block="form-section",
            visual_group_id="default_group",
            element_sequence=1,
            confidence=0.2,
            supporting_patterns=["No strong spatial pattern found"]
        )
    
    def apply_hierarchy_patterns(self, field: FormField, parent_child_map: Dict[str, List[str]]) -> HierarchySuggestion:
        """
        Apply field hierarchy patterns for parent-child relationships.
        
        Args:
            field: Current field to analyze
            parent_child_map: Mapping of parent fields to children
            
        Returns:
            Hierarchy suggestion with naming recommendations
        """
        # Check if field has a parent
        parent_field_id = field.parent_field_id if hasattr(field, 'parent_field_id') else None
        
        if parent_field_id and parent_field_id in parent_child_map:
            # Field is a child - inherit from parent
            parent_suggestion = self._analyze_parent_inheritance(field, parent_field_id)
            
            return HierarchySuggestion(
                parent_block=parent_suggestion.get('block', 'inherited'),
                element_name=parent_suggestion.get('element', field.field_type),
                modifier_suggestion=parent_suggestion.get('modifier'),
                inheritance_rules=parent_suggestion.get('rules', []),
                confidence=parent_suggestion.get('confidence', 0.7)
            )
        
        # Check if field is a parent
        if field.id in parent_child_map:
            children = parent_child_map[field.id]
            parent_suggestion = self._analyze_parent_role(field, children)
            
            return HierarchySuggestion(
                parent_block=parent_suggestion.get('block', 'group'),
                element_name=parent_suggestion.get('element', 'container'),
                modifier_suggestion=parent_suggestion.get('modifier'),
                inheritance_rules=parent_suggestion.get('rules', []),
                confidence=parent_suggestion.get('confidence', 0.6)
            )
        
        # Regular field - no special hierarchy considerations
        return HierarchySuggestion(
            parent_block="field",
            element_name=field.field_type,
            modifier_suggestion=None,
            inheritance_rules=[],
            confidence=0.3
        )
    
    def learn_from_feedback(self, field: FormField, chosen_name: str, confidence: float):
        """
        Learn from user choices to improve pattern accuracy.
        
        Args:
            field: Field that was named
            chosen_name: BEM name that was chosen/approved
            confidence: Confidence in the choice
        """
        feedback_entry = {
            'field_id': field.id,
            'field_type': field.field_type,
            'field_name': field.name,
            'chosen_bem_name': chosen_name,
            'confidence': confidence,
            'field_coordinates': field.coordinates,
            'timestamp': None  # Could add timestamp if needed
        }
        
        self.feedback_history.append(feedback_entry)
        
        # Update pattern weights based on successful choices
        self._update_pattern_weights(feedback_entry)
        
        logger.info(f"Learned from feedback: {chosen_name} (confidence: {confidence:.2f})")
    
    def _extract_context_text(self, context: FieldContext) -> str:
        """Extract and combine all text from field context."""
        text_parts = []
        
        if context.label:
            text_parts.append(context.label)
        if context.section_header:
            text_parts.append(context.section_header)
        if context.nearby_text:
            text_parts.extend(context.nearby_text)
        if hasattr(context, 'text_above') and context.text_above:
            text_parts.append(context.text_above)
        if hasattr(context, 'text_below') and context.text_below:
            text_parts.append(context.text_below)
        if hasattr(context, 'text_left') and context.text_left:
            text_parts.append(context.text_left)
        if hasattr(context, 'text_right') and context.text_right:
            text_parts.append(context.text_right)
        
        return ' '.join(text_parts).lower()
    
    def _calculate_pattern_match(self, pattern: ContextPattern, context_text: str, context: FieldContext) -> float:
        """Calculate how well a pattern matches the given context."""
        if not pattern.trigger_text:
            return 0.0
        
        # Check trigger word matches
        trigger_matches = 0
        for trigger in pattern.trigger_text:
            if trigger.lower() in context_text:
                trigger_matches += 1
        
        trigger_score = trigger_matches / len(pattern.trigger_text)
        
        # Boost score for spatial indicator matches
        spatial_boost = 0.0
        if pattern.spatial_indicators and hasattr(context, 'spatial_indicators'):
            spatial_matches = len(set(pattern.spatial_indicators) & 
                                set(getattr(context, 'spatial_indicators', [])))
            if pattern.spatial_indicators:
                spatial_boost = (spatial_matches / len(pattern.spatial_indicators)) * 0.2
        
        # Combine scores
        total_score = trigger_score + spatial_boost
        
        return min(total_score, 1.0)
    
    def _find_matching_triggers(self, pattern: ContextPattern, context_text: str) -> List[str]:
        """Find which trigger words from the pattern match the context."""
        matching = []
        for trigger in pattern.trigger_text:
            if trigger.lower() in context_text:
                matching.append(trigger)
        return matching
    
    def _check_spatial_indicators(self, pattern: ContextPattern, context: FieldContext) -> bool:
        """Check if spatial indicators match between pattern and context."""
        if not pattern.spatial_indicators or not hasattr(context, 'spatial_indicators'):
            return False
        
        context_indicators = getattr(context, 'spatial_indicators', [])
        return len(set(pattern.spatial_indicators) & set(context_indicators)) > 0
    
    def _calculate_spatial_match(self, pattern: SpatialPattern, field_x: float, field_y: float) -> float:
        """Calculate how well a field position matches a spatial pattern."""
        x_range = pattern.position_range.get('x', (0, 1000))
        y_range = pattern.position_range.get('y', (0, 1000))
        
        # Check if field is within the pattern's spatial range
        x_in_range = x_range[0] <= field_x <= x_range[1]
        y_in_range = y_range[0] <= field_y <= y_range[1]
        
        if not (x_in_range and y_in_range):
            return 0.0
        
        # Calculate distance from center of range
        x_center = (x_range[0] + x_range[1]) / 2
        y_center = (y_range[0] + y_range[1]) / 2
        
        x_distance = abs(field_x - x_center)
        y_distance = abs(field_y - y_center)
        
        # Normalize by range size
        x_range_size = x_range[1] - x_range[0]
        y_range_size = y_range[1] - y_range[0]
        
        if x_range_size > 0 and y_range_size > 0:
            x_proximity = 1.0 - (x_distance / (x_range_size / 2))
            y_proximity = 1.0 - (y_distance / (y_range_size / 2))
            
            return (x_proximity + y_proximity) / 2
        
        return 0.5  # Field is in range but can't calculate proximity
    
    def _calculate_element_sequence(self, field: FormField, all_fields: List[FormField], 
                                  pattern: SpatialPattern) -> int:
        """Calculate the sequence position of a field within its spatial group."""
        field_x = field.coordinates.get('x', 0)
        field_y = field.coordinates.get('y', 0)
        
        # Find all fields in the same spatial region
        region_fields = []
        for other_field in all_fields:
            other_x = other_field.coordinates.get('x', 0)
            other_y = other_field.coordinates.get('y', 0)
            
            if self._calculate_spatial_match(pattern, other_x, other_y) > 0.4:
                region_fields.append((other_field, other_x, other_y))
        
        # Sort by position (top-to-bottom, left-to-right)
        region_fields.sort(key=lambda x: (x[2], x[1]))  # Sort by y, then x
        
        # Find current field's position in the sequence
        for i, (region_field, _, _) in enumerate(region_fields):
            if region_field.id == field.id:
                return i + 1  # 1-based indexing
        
        return 1  # Default to first position
    
    def _analyze_parent_inheritance(self, field: FormField, parent_field_id: str) -> Dict[str, Any]:
        """Analyze inheritance patterns for child fields."""
        # Look for patterns in feedback history
        parent_patterns = []
        
        for feedback in self.feedback_history:
            if feedback['field_id'] == parent_field_id:
                parent_patterns.append(feedback)
        
        if parent_patterns:
            # Use most recent parent pattern
            latest_parent = parent_patterns[-1]
            chosen_name = latest_parent['chosen_bem_name']
            
            # Parse parent BEM name
            if '_' in chosen_name:
                parent_block = chosen_name.split('_')[0]
            else:
                parent_block = chosen_name
            
            return {
                'block': parent_block,
                'element': field.field_type,
                'modifier': f"child-{field.id[-3:]}",  # Use last 3 chars of field ID
                'rules': [f"Inherited from parent {parent_field_id}"],
                'confidence': 0.8
            }
        
        # Fallback for unknown parent
        return {
            'block': 'inherited',
            'element': field.field_type,
            'modifier': None,
            'rules': [f"Unknown parent pattern for {parent_field_id}"],
            'confidence': 0.4
        }
    
    def _analyze_parent_role(self, field: FormField, children: List[str]) -> Dict[str, Any]:
        """Analyze naming patterns for parent fields."""
        # Parent fields often represent groups or containers
        if field.field_type == 'radio':
            return {
                'block': 'selection',
                'element': 'group',
                'modifier': None,
                'rules': [f"Radio group parent with {len(children)} children"],
                'confidence': 0.9
            }
        elif len(children) > 3:
            return {
                'block': 'form-section',
                'element': 'container',
                'modifier': None,
                'rules': [f"Container field with {len(children)} children"],
                'confidence': 0.7
            }
        else:
            return {
                'block': 'field-group',
                'element': 'parent',
                'modifier': None,
                'rules': [f"Small group parent with {len(children)} children"],
                'confidence': 0.6
            }
    
    def _update_pattern_weights(self, feedback_entry: Dict[str, Any]):
        """Update pattern confidence weights based on successful choices."""
        chosen_name = feedback_entry['chosen_bem_name']
        confidence = feedback_entry['confidence']
        
        # Parse the chosen BEM name to identify patterns
        if '_' in chosen_name:
            block_part = chosen_name.split('_')[0]
            
            # Find matching context patterns and boost their confidence
            for pattern in self.patterns.context_patterns:
                if pattern.bem_block == block_part:
                    # Boost pattern confidence based on user approval
                    boost = (confidence - pattern.confidence) * 0.1  # Small adjustment
                    pattern.confidence = min(pattern.confidence + boost, 1.0)
                    
                    logger.debug(f"Boosted pattern confidence for '{block_part}': "
                               f"{pattern.confidence - boost:.3f} -> {pattern.confidence:.3f}")
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about pattern usage and effectiveness."""
        stats = {
            'total_context_patterns': len(self.patterns.context_patterns),
            'total_spatial_patterns': len(self.patterns.spatial_patterns),
            'feedback_entries': len(self.feedback_history),
            'pattern_confidence_distribution': {
                'high (>0.8)': 0,
                'medium (0.5-0.8)': 0,
                'low (<0.5)': 0
            }
        }
        
        # Calculate confidence distribution
        all_confidences = []
        all_confidences.extend([p.confidence for p in self.patterns.context_patterns])
        all_confidences.extend([p.confidence for p in self.patterns.spatial_patterns])
        
        for conf in all_confidences:
            if conf > 0.8:
                stats['pattern_confidence_distribution']['high (>0.8)'] += 1
            elif conf >= 0.5:
                stats['pattern_confidence_distribution']['medium (0.5-0.8)'] += 1
            else:
                stats['pattern_confidence_distribution']['low (<0.5)'] += 1
        
        return stats