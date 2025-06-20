"""Similarity matching system for finding training examples similar to new fields."""

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher

from ..core.field_extractor import FormField, FieldContext
from .pattern_analyzer import PatternDatabase, ContextPattern, TrainingExample
from .csv_schema import NamingPattern
import logging
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class SimilarMatch:
    """A training example similar to a new field."""
    training_example: TrainingExample
    similarity_score: float
    matching_factors: List[str]  # What made this similar
    recommended_bem: str
    confidence: float
    field_match_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BEMCandidate:
    """Candidate BEM name with generation details."""
    bem_name: str
    confidence: float
    source: str  # 'exact_match', 'pattern_adaptation', 'rule_based'
    reasoning: str  # Explanation for this suggestion
    training_examples: List[str] = field(default_factory=list)  # Supporting examples
    alternative_names: List[str] = field(default_factory=list)


@dataclass
class SimilarityFactors:
    """Factors contributing to similarity score."""
    text_similarity: float = 0.0
    spatial_similarity: float = 0.0
    type_similarity: float = 0.0
    context_similarity: float = 0.0
    visual_similarity: float = 0.0


class SimilarityMatcher:
    """Find training examples similar to new fields for pattern application."""
    
    def __init__(self, pattern_database: PatternDatabase):
        self.patterns = pattern_database
        self.similarity_cache = {}  # Cache similarity calculations
        
        # Similarity weights
        self.weights = {
            'text': 0.35,
            'spatial': 0.20,
            'type': 0.15,
            'context': 0.20,
            'visual': 0.10
        }
    
    def find_similar_contexts(self, field_context: FieldContext, 
                            training_examples: List[TrainingExample]) -> List[SimilarMatch]:
        """Find training examples with similar context."""
        logger.info(f"Finding similar contexts for field {field_context.field_id}")
        
        similar_matches = []
        
        for example in training_examples:
            # Find the most similar field in this training example
            best_match = self._find_best_field_match(field_context, example)
            
            if best_match:
                match_score, matching_factors, recommended_bem = best_match
                
                if match_score >= 0.3:  # Minimum similarity threshold
                    similar_match = SimilarMatch(
                        training_example=example,
                        similarity_score=match_score,
                        matching_factors=matching_factors,
                        recommended_bem=recommended_bem,
                        confidence=self._calculate_match_confidence(match_score, matching_factors)
                    )
                    similar_matches.append(similar_match)
        
        # Sort by similarity score
        similar_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        logger.info(f"Found {len(similar_matches)} similar contexts")
        return similar_matches[:10]  # Return top 10 matches
    
    def _find_best_field_match(self, target_context: FieldContext, 
                              example: TrainingExample) -> Optional[Tuple[float, List[str], str]]:
        """Find the best matching field in a training example."""
        best_score = 0.0
        best_factors = []
        best_bem = ""
        
        for context in example.context_data:
            # Find corresponding PDF field
            pdf_field = self._find_pdf_field(context.field_id, example.pdf_fields)
            if not pdf_field:
                continue
            
            # Get BEM name for this field
            bem_name = example.field_correlations.get(context.field_id)
            if not bem_name:
                continue
            
            # Calculate similarity
            similarity_score, factors = self.calculate_context_similarity(target_context, context, pdf_field)
            
            if similarity_score > best_score:
                best_score = similarity_score
                best_factors = factors
                best_bem = bem_name
        
        if best_score > 0:
            return (best_score, best_factors, best_bem)
        return None
    
    def _find_pdf_field(self, field_id: str, fields: List[FormField]) -> Optional[FormField]:
        """Find PDF field by ID."""
        for field in fields:
            if field.field_id == field_id:
                return field
        return None
    
    def calculate_context_similarity(self, ctx1: FieldContext, ctx2: FieldContext, 
                                   field2: FormField) -> Tuple[float, List[str]]:
        """Multi-factor similarity scoring between field contexts."""
        factors = SimilarityFactors()
        matching_factors = []
        
        # Text similarity (labels and nearby text)
        factors.text_similarity = self._calculate_text_similarity(ctx1, ctx2)
        if factors.text_similarity > 0.6:
            matching_factors.append('text_similarity')
        
        # Spatial similarity (if we have coordinates for ctx1's field)
        if hasattr(ctx1, 'coordinates') or ctx1.field_id:
            factors.spatial_similarity = self._calculate_spatial_similarity(ctx1, field2)
            if factors.spatial_similarity > 0.5:
                matching_factors.append('spatial_similarity')
        
        # Type similarity (field types)
        factors.type_similarity = self._calculate_type_similarity(ctx1, ctx2)
        if factors.type_similarity > 0.7:
            matching_factors.append('type_similarity')
        
        # Context similarity (section/hierarchy)
        factors.context_similarity = self._calculate_context_similarity(ctx1, ctx2)
        if factors.context_similarity > 0.6:
            matching_factors.append('context_similarity')
        
        # Visual similarity (grouping, styling)
        factors.visual_similarity = self._calculate_visual_similarity(ctx1, ctx2)
        if factors.visual_similarity > 0.5:
            matching_factors.append('visual_similarity')
        
        # Calculate weighted total similarity
        total_similarity = (
            factors.text_similarity * self.weights['text'] +
            factors.spatial_similarity * self.weights['spatial'] +
            factors.type_similarity * self.weights['type'] +
            factors.context_similarity * self.weights['context'] +
            factors.visual_similarity * self.weights['visual']
        )
        
        return total_similarity, matching_factors
    
    def _calculate_text_similarity(self, ctx1: FieldContext, ctx2: FieldContext) -> float:
        """Calculate text similarity between field contexts."""
        # Combine all text from both contexts
        text1 = f"{ctx1.label_text or ''} {' '.join(ctx1.nearby_text or [])}".lower()
        text2 = f"{ctx2.label_text or ''} {' '.join(ctx2.nearby_text or [])}".lower()
        
        if not text1 or not text2:
            return 0.0
        
        # Use sequence matcher for fuzzy string similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Boost similarity for exact keyword matches
        keywords1 = set(re.findall(r'\b\w{3,}\b', text1))
        keywords2 = set(re.findall(r'\b\w{3,}\b', text2))
        
        if keywords1 and keywords2:
            keyword_overlap = len(keywords1 & keywords2) / len(keywords1 | keywords2)
            similarity = max(similarity, keyword_overlap)
        
        return similarity
    
    def _calculate_spatial_similarity(self, ctx1: FieldContext, field2: FormField) -> float:
        """Calculate spatial similarity between fields."""
        # This is a simplified implementation
        # In practice, we'd need coordinates for both fields
        
        # For now, assume some spatial similarity based on page or section
        if hasattr(ctx1, 'page_number') and hasattr(field2, 'page_number'):
            if getattr(ctx1, 'page_number', 1) == getattr(field2, 'page_number', 1):
                return 0.7  # Same page
            else:
                return 0.2  # Different page
        
        return 0.5  # Default moderate similarity
    
    def _calculate_type_similarity(self, ctx1: FieldContext, ctx2: FieldContext) -> float:
        """Calculate field type similarity."""
        # Get field types if available
        type1 = getattr(ctx1, 'field_type', 'unknown')
        type2 = getattr(ctx2, 'field_type', 'unknown')
        
        if type1 == type2:
            return 1.0
        
        # Similar types (text variations)
        text_types = {'text', 'textfield', 'input', 'string'}
        if type1.lower() in text_types and type2.lower() in text_types:
            return 0.8
        
        # Boolean/choice types
        choice_types = {'checkbox', 'radio', 'choice', 'button'}
        if type1.lower() in choice_types and type2.lower() in choice_types:
            return 0.8
        
        return 0.3  # Different types but still some similarity
    
    def _calculate_context_similarity(self, ctx1: FieldContext, ctx2: FieldContext) -> float:
        """Calculate contextual similarity (section, hierarchy)."""
        similarity = 0.0
        
        # Section similarity
        section1 = getattr(ctx1, 'section', None)
        section2 = getattr(ctx2, 'section', None)
        
        if section1 and section2:
            if section1 == section2:
                similarity += 0.5
            elif any(word in section2.lower() for word in section1.lower().split()):
                similarity += 0.3
        
        # Visual grouping similarity
        group1 = getattr(ctx1, 'visual_group_id', None)
        group2 = getattr(ctx2, 'visual_group_id', None)
        
        if group1 and group2 and group1 == group2:
            similarity += 0.3
        
        # Hierarchy level similarity
        level1 = getattr(ctx1, 'hierarchy_level', 0)
        level2 = getattr(ctx2, 'hierarchy_level', 0)
        
        if level1 == level2:
            similarity += 0.2
        
        return min(similarity, 1.0)
    
    def _calculate_visual_similarity(self, ctx1: FieldContext, ctx2: FieldContext) -> float:
        """Calculate visual/styling similarity."""
        # This is a simplified implementation
        # In practice, we might compare font sizes, colors, positioning patterns
        
        similarity = 0.5  # Default moderate similarity
        
        # If both have styling information, compare it
        style1 = getattr(ctx1, 'styling', {})
        style2 = getattr(ctx2, 'styling', {})
        
        if style1 and style2:
            common_styles = set(style1.keys()) & set(style2.keys())
            if common_styles:
                matching_styles = sum(1 for key in common_styles if style1[key] == style2[key])
                similarity = matching_styles / len(common_styles)
        
        return similarity
    
    def _calculate_match_confidence(self, similarity_score: float, matching_factors: List[str]) -> float:
        """Calculate confidence in the similarity match."""
        # Base confidence on similarity score
        base_confidence = similarity_score
        
        # Boost confidence based on number and type of matching factors
        factor_boost = len(matching_factors) * 0.1
        
        # Special boost for strong text similarity
        if 'text_similarity' in matching_factors:
            factor_boost += 0.1
        
        # Special boost for multiple factors
        if len(matching_factors) >= 3:
            factor_boost += 0.1
        
        return min(base_confidence + factor_boost, 1.0)
    
    def rank_bem_candidates(self, field: FormField, context: FieldContext,
                          training_examples: List[TrainingExample]) -> List[BEMCandidate]:
        """Generate ranked list of BEM name candidates."""
        logger.info(f"Ranking BEM candidates for field {field.field_id}")
        
        candidates = []
        
        # 1. Find exact pattern matches from training data
        exact_matches = self._find_exact_pattern_matches(context)
        candidates.extend(exact_matches)
        
        # 2. Find similar context patterns with adaptation
        similar_matches = self.find_similar_contexts(context, training_examples)
        adapted_candidates = self._create_adapted_candidates(similar_matches, context)
        candidates.extend(adapted_candidates)
        
        # 3. Apply rule-based fallbacks for novel cases
        if len(candidates) < 3:  # Need more candidates
            rule_based = self._generate_rule_based_candidates(context, field)
            candidates.extend(rule_based)
        
        # Remove duplicates and sort by confidence
        unique_candidates = self._deduplicate_candidates(candidates)
        unique_candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"Generated {len(unique_candidates)} BEM candidates")
        return unique_candidates[:5]  # Return top 5 candidates
    
    def _find_exact_pattern_matches(self, context: FieldContext) -> List[BEMCandidate]:
        """Find exact pattern matches from training data."""
        candidates = []
        
        # Check context patterns for exact matches
        context_text = f"{context.label_text or ''} {' '.join(context.nearby_text or [])}".lower()
        
        for pattern in self.patterns.context_patterns:
            # Check if any trigger words match
            if any(trigger in context_text for trigger in pattern.trigger_text):
                bem_name = f"{pattern.bem_block}_{pattern.bem_element}" if pattern.bem_element else pattern.bem_block
                
                candidate = BEMCandidate(
                    bem_name=bem_name,
                    confidence=pattern.confidence,
                    source='exact_match',
                    reasoning=f"Exact pattern match with triggers: {', '.join(pattern.trigger_text)}",
                    training_examples=pattern.examples
                )
                candidates.append(candidate)
        
        return candidates
    
    def _create_adapted_candidates(self, similar_matches: List[SimilarMatch], 
                                 context: FieldContext) -> List[BEMCandidate]:
        """Create adapted candidates from similar matches."""
        candidates = []
        
        for match in similar_matches[:3]:  # Top 3 similar matches
            # Use the recommended BEM name but adapt if needed
            base_bem = match.recommended_bem
            
            # Simple adaptation: keep block, adapt element based on context
            if '_' in base_bem:
                block = base_bem.split('_')[0]
                
                # Try to adapt element based on context
                adapted_element = self._adapt_element_name(context)
                if adapted_element:
                    adapted_bem = f"{block}_{adapted_element}"
                else:
                    adapted_bem = base_bem
            else:
                adapted_bem = base_bem
            
            candidate = BEMCandidate(
                bem_name=adapted_bem,
                confidence=match.confidence * 0.9,  # Slightly lower confidence for adaptation
                source='pattern_adaptation',
                reasoning=f"Adapted from similar field with {match.similarity_score:.2f} similarity ({', '.join(match.matching_factors)})",
                training_examples=[match.recommended_bem]
            )
            candidates.append(candidate)
        
        return candidates
    
    def _adapt_element_name(self, context: FieldContext) -> Optional[str]:
        """Adapt element name based on context."""
        context_text = f"{context.label_text or ''} {' '.join(context.nearby_text or [])}".lower()
        
        # Simple keyword-based adaptation
        element_keywords = {
            'name': ['name', 'first', 'last', 'full'],
            'address': ['address', 'street', 'location'],
            'phone': ['phone', 'telephone', 'number'],
            'email': ['email', 'e-mail', 'electronic'],
            'date': ['date', 'time', 'when'],
            'amount': ['amount', 'value', 'price', 'cost'],
            'signature': ['signature', 'sign', 'initial']
        }
        
        for element, keywords in element_keywords.items():
            if any(keyword in context_text for keyword in keywords):
                return element
        
        return None
    
    def _generate_rule_based_candidates(self, context: FieldContext, 
                                      field: FormField) -> List[BEMCandidate]:
        """Generate rule-based candidates as fallback."""
        candidates = []
        
        # Simple rule-based generation based on field properties
        context_text = f"{context.label_text or ''} {' '.join(context.nearby_text or [])}".lower()
        field_type = field.field_type or 'text'
        
        # Determine block based on common patterns
        if any(word in context_text for word in ['owner', 'insured', 'applicant']):
            block = 'owner'
        elif any(word in context_text for word in ['contact', 'phone', 'email']):
            block = 'contact'
        elif any(word in context_text for word in ['payment', 'premium', 'amount']):
            block = 'payment'
        elif any(word in context_text for word in ['signature', 'sign', 'acknowledgment']):
            block = 'signature'
        else:
            block = 'general'
        
        # Determine element based on context
        element = self._adapt_element_name(context) or 'field'
        
        bem_name = f"{block}_{element}"
        
        candidate = BEMCandidate(
            bem_name=bem_name,
            confidence=0.5,  # Moderate confidence for rule-based
            source='rule_based',
            reasoning=f"Rule-based generation from field type '{field_type}' and context keywords",
            training_examples=[]
        )
        candidates.append(candidate)
        
        return candidates
    
    def _deduplicate_candidates(self, candidates: List[BEMCandidate]) -> List[BEMCandidate]:
        """Remove duplicate candidates and merge similar ones."""
        unique_candidates = {}
        
        for candidate in candidates:
            bem_name = candidate.bem_name
            
            if bem_name in unique_candidates:
                # Keep the one with higher confidence
                if candidate.confidence > unique_candidates[bem_name].confidence:
                    unique_candidates[bem_name] = candidate
            else:
                unique_candidates[bem_name] = candidate
        
        return list(unique_candidates.values())