"""
Smart BEM Name Generator

Generate BEM names using training patterns combined with field context from Phase 1.
Implements multi-stage approach: exact patterns -> similar context -> rule-based fallback.
"""

import re
from dataclasses import dataclass, field as dataclass_field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

from ..core.field_extractor import FormField, FieldContext
from ..training.pattern_analyzer import PatternDatabase, ContextPattern, SpatialPattern
from ..training.similarity_matcher import SimilarityMatcher, SimilarMatch
from ..utils.logging import get_logger

logger = get_logger(__name__)


class GenerationMethod(Enum):
    """Methods used for BEM name generation."""
    EXACT_PATTERN_MATCH = "exact_pattern_match"
    SIMILAR_CONTEXT_ADAPTATION = "similar_context_adaptation"
    RULE_BASED_GENERATION = "rule_based_generation"
    FALLBACK_DEFAULT = "fallback_default"


@dataclass
class BEMCandidate:
    """A candidate BEM name with confidence and reasoning."""
    bem_name: str
    confidence: float
    source: GenerationMethod
    reasoning: str
    training_examples: List[str] = dataclass_field(default_factory=list)
    pattern_match_score: float = 0.0
    uniqueness_validated: bool = False


@dataclass
class BEMResult:
    """Result of BEM name generation with alternatives."""
    bem_name: str
    confidence: float
    generation_method: GenerationMethod
    reasoning: str
    alternatives: List[BEMCandidate] = dataclass_field(default_factory=list)
    validation_status: str = "pending"
    field_id: str = ""


class BEMNameGenerator:
    """Generate BEM names using training patterns and field context."""
    
    def __init__(self, pattern_database: PatternDatabase, similarity_matcher: SimilarityMatcher):
        """Initialize with pattern database and similarity matcher."""
        self.patterns = pattern_database
        self.matcher = similarity_matcher
        self.generated_names = set()  # Track uniqueness
        
        # BEM validation pattern - no consecutive hyphens allowed
        self.bem_pattern = re.compile(
            r'^[a-z]([a-z0-9]|-(?!-|$))*(_[a-z]([a-z0-9]|-(?!-|$))*)?(__[a-z]([a-z0-9]|-(?!-|$))*)?$'
        )
        
        logger.info(f"BEMNameGenerator initialized with {len(pattern_database.context_patterns)} "
                   f"context patterns and {len(pattern_database.spatial_patterns)} spatial patterns")
    
    def generate_bem_name(self, field: FormField, context: FieldContext) -> BEMResult:
        """
        Primary BEM name generation using multi-stage approach:
        1. Exact pattern matching from training data
        2. Similar context adaptation  
        3. Rule-based generation for novel cases
        4. Validation and uniqueness checking
        """
        logger.debug(f"Generating BEM name for field {field.id} ({field.name})")
        
        candidates = []
        
        # Stage 1: Try exact pattern matching
        exact_matches = self._find_exact_pattern_matches(field, context)
        candidates.extend(exact_matches)
        
        # Stage 2: Try similar context adaptation
        if not candidates or max(c.confidence for c in candidates) < 0.8:
            similar_matches = self._find_similar_context_matches(field, context)
            candidates.extend(similar_matches)
        
        # Stage 3: Rule-based generation for novel cases
        if not candidates or max(c.confidence for c in candidates) < 0.6:
            rule_based = self._generate_rule_based_name(field, context)
            if rule_based:
                candidates.append(rule_based)
        
        # Stage 4: Fallback if nothing else works
        if not candidates:
            fallback = self._generate_fallback_name(field, context)
            candidates.append(fallback)
        
        # Select best candidate
        best_candidate = self._select_best_candidate(candidates)
        
        # Ensure uniqueness
        final_name = self._ensure_uniqueness(best_candidate.bem_name, field.id)
        
        # Validate BEM compliance
        validation_status = "valid" if self._validate_bem_syntax(final_name) else "invalid_syntax"
        
        result = BEMResult(
            bem_name=final_name,
            confidence=best_candidate.confidence,
            generation_method=best_candidate.source,
            reasoning=best_candidate.reasoning,
            alternatives=candidates[:3],  # Top 3 alternatives
            validation_status=validation_status,
            field_id=field.id
        )
        
        # Track generated name
        self.generated_names.add(final_name)
        
        logger.debug(f"Generated BEM name '{final_name}' with confidence {best_candidate.confidence:.2f}")
        return result
    
    def _find_exact_pattern_matches(self, field: FormField, context: FieldContext) -> List[BEMCandidate]:
        """Find exact pattern matches from training data."""
        candidates = []
        
        # Check context patterns
        for pattern in self.patterns.context_patterns:
            match_score = self._calculate_context_match_score(pattern, context)
            
            if match_score > 0.8:  # High threshold for exact matches
                bem_name = self._construct_bem_name(
                    pattern.bem_block,
                    pattern.bem_element,
                    self._infer_modifier(field, context)
                )
                
                candidate = BEMCandidate(
                    bem_name=bem_name,
                    confidence=match_score * 0.95,  # Slight reduction for being pattern-based
                    source=GenerationMethod.EXACT_PATTERN_MATCH,
                    reasoning=f"Exact match with training pattern: {', '.join(pattern.trigger_text[:3])}",
                    training_examples=pattern.examples,
                    pattern_match_score=match_score
                )
                candidates.append(candidate)
        
        return sorted(candidates, key=lambda x: x.confidence, reverse=True)
    
    def _find_similar_context_matches(self, field: FormField, context: FieldContext) -> List[BEMCandidate]:
        """Find similar contexts and adapt their BEM names."""
        candidates = []
        
        # Use similarity matcher to find similar contexts
        # Note: For now, we'll use empty training examples since we don't have them loaded
        similar_matches = self.matcher.find_similar_contexts(context, [])
        
        for match in similar_matches[:5]:  # Top 5 similar matches
            if match.similarity_score > 0.6:
                # Adapt the BEM name from similar context
                adapted_name = self._adapt_bem_name(match.recommended_bem, field, context)
                
                candidate = BEMCandidate(
                    bem_name=adapted_name,
                    confidence=match.similarity_score * 0.85,  # Reduce confidence for adaptation
                    source=GenerationMethod.SIMILAR_CONTEXT_ADAPTATION,
                    reasoning=f"Adapted from similar context: {', '.join(match.matching_factors[:2])}",
                    training_examples=[match.recommended_bem],
                    pattern_match_score=match.similarity_score
                )
                candidates.append(candidate)
        
        return sorted(candidates, key=lambda x: x.confidence, reverse=True)
    
    def _generate_rule_based_name(self, field: FormField, context: FieldContext) -> Optional[BEMCandidate]:
        """Generate BEM name using rule-based approach."""
        # Import here to avoid circular imports
        from .rule_engine import RuleBasedEngine
        
        rule_engine = RuleBasedEngine()
        rule_result = rule_engine.generate_fallback_name(field, context)
        
        if rule_result:
            return BEMCandidate(
                bem_name=rule_result.bem_name,
                confidence=rule_result.confidence,
                source=GenerationMethod.RULE_BASED_GENERATION,
                reasoning=rule_result.reasoning,
                training_examples=[],
                pattern_match_score=0.0
            )
        
        return None
    
    def _generate_fallback_name(self, field: FormField, context: FieldContext) -> BEMCandidate:
        """Generate fallback name when all else fails."""
        # Create basic BEM name from field properties
        block = self._infer_block_from_context(context) or "form-field"
        element = self._infer_element_from_field(field) or "input"
        modifier = None
        
        bem_name = self._construct_bem_name(block, element, modifier)
        
        return BEMCandidate(
            bem_name=bem_name,
            confidence=0.3,  # Low confidence for fallback
            source=GenerationMethod.FALLBACK_DEFAULT,
            reasoning="Fallback generation from field properties",
            training_examples=[],
            pattern_match_score=0.0
        )
    
    def _calculate_context_match_score(self, pattern: ContextPattern, context: FieldContext) -> float:
        """Calculate how well a context pattern matches the given context."""
        score = 0.0
        
        # Combine all context text
        context_text = f"{context.label or ''} {' '.join(context.nearby_text or [])}".lower()
        
        # Check trigger text matches
        trigger_matches = 0
        for trigger in pattern.trigger_text:
            if trigger.lower() in context_text:
                trigger_matches += 1
        
        if pattern.trigger_text:
            trigger_score = trigger_matches / len(pattern.trigger_text)
            score += trigger_score * 0.7  # 70% weight for triggers
        
        # Check spatial indicators if available
        if pattern.spatial_indicators and hasattr(context, 'spatial_indicators'):
            spatial_matches = 0
            for indicator in pattern.spatial_indicators:
                if indicator in getattr(context, 'spatial_indicators', []):
                    spatial_matches += 1
            
            if pattern.spatial_indicators:
                spatial_score = spatial_matches / len(pattern.spatial_indicators)
                score += spatial_score * 0.3  # 30% weight for spatial
        
        return min(score, 1.0)
    
    def _construct_bem_name(self, block: str, element: Optional[str], modifier: Optional[str]) -> str:
        """Construct valid BEM name from components."""
        bem_name = self._sanitize_bem_component(block)
        
        if element:
            bem_name += f"_{self._sanitize_bem_component(element)}"
        
        if modifier:
            bem_name += f"__{self._sanitize_bem_component(modifier)}"
        
        return bem_name
    
    def _sanitize_bem_component(self, component: str) -> str:
        """Sanitize component to be BEM-compliant."""
        if not component:
            return ""
        
        # Convert to lowercase and replace invalid characters
        sanitized = re.sub(r'[^a-z0-9-]', '-', component.lower())
        
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = f"field-{sanitized}"
        
        return sanitized or "field"
    
    def _infer_modifier(self, field: FormField, context: FieldContext) -> Optional[str]:
        """Infer modifier from field properties and context."""
        modifiers = []
        
        # Check field properties
        if field.properties.get('required', False):
            modifiers.append('required')
        elif field.properties.get('readonly', False):
            modifiers.append('readonly')
        
        # Check context for positional modifiers
        context_text = f"{context.label or ''} {' '.join(context.nearby_text or [])}".lower()
        
        if any(word in context_text for word in ['first', 'primary', 'main']):
            modifiers.append('primary')
        elif any(word in context_text for word in ['second', 'secondary', 'additional']):
            modifiers.append('secondary')
        elif any(word in context_text for word in ['last', 'final']):
            modifiers.append('final')
        
        return modifiers[0] if modifiers else None
    
    def _infer_block_from_context(self, context: FieldContext) -> Optional[str]:
        """Infer block name from context."""
        context_text = f"{context.section_header or ''} {context.label or ''}".lower()
        
        # Common block patterns
        if any(word in context_text for word in ['owner', 'applicant', 'insured']):
            return 'owner-information'
        elif any(word in context_text for word in ['beneficiary', 'recipient']):
            return 'beneficiary-information'
        elif any(word in context_text for word in ['payment', 'premium', 'billing']):
            return 'payment'
        elif any(word in context_text for word in ['signature', 'sign', 'authorization']):
            return 'signatures'
        elif any(word in context_text for word in ['contact', 'address', 'phone']):
            return 'contact-information'
        
        return None
    
    def _infer_element_from_field(self, field: FormField) -> Optional[str]:
        """Infer element name from field properties."""
        field_name = (field.name or '').lower()
        field_type = field.field_type.lower()
        
        # Name fields
        if any(word in field_name for word in ['name', 'fname', 'lname']):
            return 'name'
        # Address fields  
        elif any(word in field_name for word in ['address', 'street', 'city', 'state', 'zip']):
            return 'address'
        # Phone fields
        elif any(word in field_name for word in ['phone', 'tel', 'mobile']):
            return 'phone'
        # Email fields
        elif any(word in field_name for word in ['email', 'mail']):
            return 'email'
        # Date fields
        elif any(word in field_name for word in ['date', 'birth', 'dob']):
            return 'date'
        # Amount/value fields
        elif any(word in field_name for word in ['amount', 'value', 'dollar']):
            return 'amount'
        # Type-based fallbacks
        elif field_type == 'signature':
            return 'signature'
        elif field_type in ['radio', 'checkbox']:
            return 'selection'
        elif field_type == 'text':
            return 'input'
        
        return None
    
    def _adapt_bem_name(self, base_name: str, field: FormField, context: FieldContext) -> str:
        """Adapt a BEM name from similar context to current field."""
        # Parse the base BEM name
        parts = self._parse_bem_name(base_name)
        if not parts:
            return base_name
        
        block, element, modifier = parts
        
        # Keep the block, adapt element and modifier
        new_element = self._infer_element_from_field(field) or element
        new_modifier = self._infer_modifier(field, context) or modifier
        
        return self._construct_bem_name(block, new_element, new_modifier)
    
    def _parse_bem_name(self, bem_name: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """Parse BEM name into components."""
        try:
            # Handle modifiers (--)
            parts = bem_name.split('__')
            base = parts[0]
            modifier = parts[1] if len(parts) > 1 else None
            
            # Handle block_element structure
            if '_' in base:
                base_parts = base.split('_')
                block = '_'.join(base_parts[:-1])
                element = base_parts[-1]
            else:
                block = base
                element = None
            
            return (block, element, modifier)
        
        except Exception:
            return None
    
    def _select_best_candidate(self, candidates: List[BEMCandidate]) -> BEMCandidate:
        """Select the best candidate from the list."""
        if not candidates:
            raise ValueError("No candidates provided")
        
        # Sort by confidence and pattern match score
        candidates.sort(key=lambda x: (x.confidence, x.pattern_match_score), reverse=True)
        
        return candidates[0]
    
    def _ensure_uniqueness(self, bem_name: str, field_id: str) -> str:
        """Ensure BEM name is unique within the current document."""
        if bem_name not in self.generated_names:
            return bem_name
        
        # Try adding modifiers
        for i in range(2, 10):
            candidate = f"{bem_name}__{i}"
            if candidate not in self.generated_names:
                logger.debug(f"Ensuring uniqueness: {bem_name} -> {candidate}")
                return candidate
        
        # Fallback with field ID
        unique_name = f"{bem_name}__field-{field_id}"
        logger.warning(f"Using field ID for uniqueness: {bem_name} -> {unique_name}")
        return unique_name
    
    def _validate_bem_syntax(self, bem_name: str) -> bool:
        """Validate BEM name syntax compliance."""
        return bool(self.bem_pattern.match(bem_name))
    
    def generate_block_name(self, context: FieldContext, spatial_group: str) -> str:
        """Generate block name based on context and spatial grouping."""
        # Try context-based inference
        block = self._infer_block_from_context(context)
        if block:
            return block
        
        # Use spatial group if available
        if spatial_group:
            return self._sanitize_bem_component(spatial_group)
        
        # Default fallback
        return "form-section"
    
    def generate_element_name(self, field: FormField, context: FieldContext) -> str:
        """Generate element name based on field and context."""
        element = self._infer_element_from_field(field)
        if element:
            return element
        
        # Try context-based inference
        if context.label:
            return self._sanitize_bem_component(context.label)
        
        # Type-based fallback
        type_map = {
            'text': 'input',
            'checkbox': 'checkbox',
            'radio': 'option',
            'choice': 'selection',
            'signature': 'signature'
        }
        
        return type_map.get(field.field_type, 'field')
    
    def generate_modifier_name(self, field: FormField, context: FieldContext, existing_names: List[str]) -> Optional[str]:
        """Generate modifier for disambiguation when needed."""
        return self._infer_modifier(field, context)
    
    def validate_bem_name(self, name: str, existing_names: List[str]) -> Dict[str, Any]:
        """Comprehensive BEM validation."""
        result = {
            'is_valid': False,
            'syntax_valid': False,
            'is_unique': False,
            'errors': [],
            'warnings': []
        }
        
        # Syntax validation
        if self._validate_bem_syntax(name):
            result['syntax_valid'] = True
        else:
            result['errors'].append(f"Invalid BEM syntax: {name}")
        
        # Uniqueness validation
        if name not in existing_names:
            result['is_unique'] = True
        else:
            result['errors'].append(f"Name already exists: {name}")
        
        # Length validation
        if len(name) > 100:
            result['warnings'].append(f"Name is very long ({len(name)} chars): {name}")
        elif len(name) < 3:
            result['errors'].append(f"Name is too short: {name}")
        
        # Overall validity
        result['is_valid'] = result['syntax_valid'] and result['is_unique'] and len(name) >= 3
        
        return result