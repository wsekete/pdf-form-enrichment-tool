"""
Hybrid Name Generation System

Orchestrates multiple BEM naming approaches to generate optimal field names.
This system combines rule-based, AI-powered, and pattern learning approaches
to provide the best possible BEM naming suggestions.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from .bem_engine import BEMNamingEngine, BEMNameCandidate, BEMValidationResult
from .preservation_generator import PreservationBEMGenerator
from ..ai.context_analyzer import AIContextAnalyzer, ContextAnalysisResult
from ..training.ai_pattern_learner import AIPatternLearner, PatternPrediction
from ..training.data_loader import TrainingDataLoader, FieldContext
from ..core.field_extractor import FormField, FieldType
from ..utils.logging import get_logger
from ..utils.errors import AIIntegrationError

logger = get_logger(__name__)


class GenerationApproach(Enum):
    """Available name generation approaches"""
    PRESERVATION = "preservation"
    RULE_BASED = "rule_based"
    AI_POWERED = "ai_powered"
    PATTERN_LEARNING = "pattern_learning"
    HYBRID_CONSENSUS = "hybrid_consensus"


@dataclass
class NameCandidate:
    """A BEM name candidate with comprehensive metadata"""
    name: str
    confidence: float
    source: GenerationApproach
    rationale: str
    validation_result: Optional[BEMValidationResult] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class GenerationResult:
    """Result of hybrid name generation"""
    field_id: str
    selected_candidate: NameCandidate
    all_candidates: List[NameCandidate]
    consensus_score: float
    processing_time: float
    approach_used: GenerationApproach
    explanation: str
    error: Optional[str] = None


@dataclass
class HybridConfig:
    """Configuration for hybrid generation system"""
    enable_ai_analysis: bool = True
    enable_pattern_learning: bool = True
    enable_preservation_mode: bool = True
    confidence_threshold: float = 0.7
    consensus_weight: float = 0.8
    max_processing_time: float = 30.0
    fallback_to_rules: bool = True


class HybridNameGenerator:
    """
    Intelligent name generation system that combines multiple approaches.
    
    This system implements the complete hybrid approach as specified in the
    original task list. It:
    
    - Combines rule-based and AI approaches for optimal results
    - Implements multi-approach scoring and selection
    - Uses confidence-based approach selection
    - Provides consensus mechanism for conflicting suggestions
    - Maintains detailed decision audit trail
    - Creates ranked name suggestion system
    """
    
    def __init__(self, config: HybridConfig = None, openai_api_key: str = None):
        """
        Initialize the hybrid name generation system.
        
        Args:
            config: Configuration for the hybrid system
            openai_api_key: OpenAI API key for AI analysis (optional)
        """
        
        self.config = config or HybridConfig()
        
        # Initialize core components
        self.bem_engine = BEMNamingEngine()
        self.preservation_generator = PreservationBEMGenerator()
        
        # Initialize training data and pattern learning
        self.training_loader = TrainingDataLoader()
        self.pattern_learner = AIPatternLearner(self.training_loader)
        
        # Initialize AI analyzer if enabled and API key available
        self.ai_analyzer = None
        if self.config.enable_ai_analysis and openai_api_key:
            try:
                self.ai_analyzer = AIContextAnalyzer(
                    api_key=openai_api_key,
                    cache_enabled=True
                )
                logger.info("AI Context Analyzer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize AI analyzer: {str(e)}")
                self.config.enable_ai_analysis = False
        else:
            self.config.enable_ai_analysis = False
        
        # Generation statistics
        self.generation_stats = {
            'total_generations': 0,
            'approach_usage': {approach.value: 0 for approach in GenerationApproach},
            'average_confidence': 0.0,
            'average_processing_time': 0.0,
            'consensus_rate': 0.0
        }
        
        logger.info(f"Hybrid Name Generator initialized with AI: {self.config.enable_ai_analysis}")
    
    async def generate_name_candidates(self, field: FormField, context: FieldContext, 
                                     existing_names: List[str] = None) -> List[NameCandidate]:
        """
        Generate multiple BEM name candidates using all available approaches.
        
        Args:
            field: Form field to generate names for
            context: Extracted context information
            existing_names: List of existing field names for uniqueness checking
            
        Returns:
            List of NameCandidate objects sorted by confidence
        """
        
        start_time = time.time()
        candidates = []
        existing_names = existing_names or []
        
        # Approach 1: Preservation Mode (if enabled)
        if self.config.enable_preservation_mode:
            preservation_candidates = await self._generate_preservation_candidates(field, context)
            candidates.extend(preservation_candidates)
        
        # Approach 2: Rule-Based BEM Engine
        rule_candidates = self._generate_rule_based_candidates(field, context)
        candidates.extend(rule_candidates)
        
        # Approach 3: AI-Powered Analysis (if enabled)
        if self.config.enable_ai_analysis and self.ai_analyzer:
            ai_candidates = await self._generate_ai_candidates(field, context)
            candidates.extend(ai_candidates)
        
        # Approach 4: Pattern Learning (if enabled)
        if self.config.enable_pattern_learning:
            pattern_candidates = self._generate_pattern_learning_candidates(field, context)
            candidates.extend(pattern_candidates)
        
        # Validate all candidates
        validated_candidates = self._validate_candidates(candidates, existing_names)
        
        # Remove duplicates and rank by confidence
        unique_candidates = self._deduplicate_and_rank_candidates(validated_candidates)
        
        processing_time = time.time() - start_time
        
        logger.debug(f"Generated {len(unique_candidates)} candidates for field {field.id} in {processing_time:.2f}s")
        
        return unique_candidates
    
    async def select_best_candidate(self, candidates: List[NameCandidate], 
                                  field: FormField, context: FieldContext) -> NameCandidate:
        """
        Select the best candidate using consensus mechanism and confidence scoring.
        
        Args:
            candidates: List of name candidates
            field: Original form field
            context: Field context
            
        Returns:
            Selected best NameCandidate
        """
        
        if not candidates:
            # Generate fallback candidate
            fallback = NameCandidate(
                name="general_field__input",
                confidence=0.1,
                source=GenerationApproach.RULE_BASED,
                rationale="Fallback name generated due to no candidates",
                processing_time=0.0
            )
            return fallback
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Multi-approach consensus scoring
        consensus_scores = self._calculate_consensus_scores(candidates)
        
        # Select candidate with highest consensus score
        best_candidate = max(candidates, key=lambda c: consensus_scores.get(c.name, 0.0))
        
        # Update confidence based on consensus
        consensus_confidence = consensus_scores.get(best_candidate.name, 0.0)
        best_candidate.confidence = min(
            best_candidate.confidence + (consensus_confidence * 0.2), 
            1.0
        )
        
        return best_candidate
    
    async def generate_complete_result(self, field: FormField, context: FieldContext,
                                     existing_names: List[str] = None) -> GenerationResult:
        """
        Generate complete naming result with full analysis and explanation.
        
        Args:
            field: Form field to generate name for
            context: Field context information
            existing_names: Existing field names for uniqueness
            
        Returns:
            Complete GenerationResult with selected name and metadata
        """
        
        start_time = time.time()
        
        try:
            # Generate all candidates
            candidates = await self.generate_name_candidates(field, context, existing_names)
            
            # Select best candidate
            selected_candidate = await self.select_best_candidate(candidates, field, context)
            
            # Calculate consensus score
            consensus_score = self._calculate_overall_consensus(candidates)
            
            # Generate explanation
            explanation = await self._generate_result_explanation(
                field, context, selected_candidate, candidates
            )
            
            processing_time = time.time() - start_time
            
            result = GenerationResult(
                field_id=field.id,
                selected_candidate=selected_candidate,
                all_candidates=candidates,
                consensus_score=consensus_score,
                processing_time=processing_time,
                approach_used=selected_candidate.source,
                explanation=explanation
            )
            
            # Update statistics
            self._update_generation_stats(result)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(f"Hybrid generation failed for field {field.id}: {str(e)}")
            
            # Return error result with fallback
            fallback_candidate = NameCandidate(
                name="general_field__input",
                confidence=0.1,
                source=GenerationApproach.RULE_BASED,
                rationale=f"Fallback due to error: {str(e)}",
                processing_time=processing_time
            )
            
            return GenerationResult(
                field_id=field.id,
                selected_candidate=fallback_candidate,
                all_candidates=[fallback_candidate],
                consensus_score=0.0,
                processing_time=processing_time,
                approach_used=GenerationApproach.RULE_BASED,
                explanation=f"Error occurred during generation: {str(e)}",
                error=str(e)
            )
    
    async def _generate_preservation_candidates(self, field: FormField, 
                                              context: FieldContext) -> List[NameCandidate]:
        """Generate candidates using preservation mode"""
        
        candidates = []
        start_time = time.time()
        
        try:
            # Use existing preservation generator
            preservation_result = self.preservation_generator.generate_bem_names(
                [field], [context], self.training_loader.load_all_training_data()
            )
            
            if field.id in preservation_result:
                bem_mapping = preservation_result[field.id]
                
                candidate = NameCandidate(
                    name=bem_mapping.new_name,
                    confidence=bem_mapping.confidence,
                    source=GenerationApproach.PRESERVATION,
                    rationale=bem_mapping.reasoning,
                    processing_time=time.time() - start_time,
                    metadata={
                        'action': bem_mapping.action,
                        'original_name': bem_mapping.original_name
                    }
                )
                
                candidates.append(candidate)
                
        except Exception as e:
            logger.debug(f"Preservation generation failed: {str(e)}")
        
        return candidates
    
    def _generate_rule_based_candidates(self, field: FormField, 
                                      context: FieldContext) -> List[NameCandidate]:
        """Generate candidates using rule-based BEM engine"""
        
        candidates = []
        start_time = time.time()
        
        try:
            bem_candidates = self.bem_engine.generate_bem_candidates(field, context)
            
            for bem_candidate in bem_candidates:
                candidate = NameCandidate(
                    name=bem_candidate.name,
                    confidence=bem_candidate.confidence,
                    source=GenerationApproach.RULE_BASED,
                    rationale=bem_candidate.rationale,
                    processing_time=time.time() - start_time,
                    metadata={
                        'rule_applied': bem_candidate.rule_applied,
                        'components': bem_candidate.components
                    }
                )
                
                candidates.append(candidate)
                
        except Exception as e:
            logger.debug(f"Rule-based generation failed: {str(e)}")
        
        return candidates
    
    async def _generate_ai_candidates(self, field: FormField, 
                                    context: FieldContext) -> List[NameCandidate]:
        """Generate candidates using AI analysis"""
        
        candidates = []
        
        if not self.ai_analyzer:
            return candidates
        
        start_time = time.time()
        
        try:
            # Get AI analysis
            analysis_result = await self.ai_analyzer.analyze_field_context(field, context)
            
            # Convert AI suggestions to candidates
            for suggestion in analysis_result.bem_suggestions:
                candidate = NameCandidate(
                    name=suggestion['name'],
                    confidence=suggestion['confidence'],
                    source=GenerationApproach.AI_POWERED,
                    rationale=suggestion.get('reasoning', 'AI-generated suggestion'),
                    processing_time=time.time() - start_time,
                    metadata={
                        'ai_model': analysis_result.ai_model_used,
                        'semantic_understanding': analysis_result.semantic_understanding,
                        'suggestion_source': suggestion.get('source', 'ai')
                    }
                )
                
                candidates.append(candidate)
                
        except Exception as e:
            logger.debug(f"AI generation failed: {str(e)}")
        
        return candidates
    
    def _generate_pattern_learning_candidates(self, field: FormField, 
                                            context: FieldContext) -> List[NameCandidate]:
        """Generate candidates using pattern learning"""
        
        candidates = []
        start_time = time.time()
        
        try:
            # Get pattern prediction
            pattern_prediction = self.pattern_learner.predict_bem_name(
                context, field.field_type.value if field.field_type else "unknown"
            )
            
            if pattern_prediction:
                candidate = NameCandidate(
                    name=pattern_prediction.suggested_name,
                    confidence=pattern_prediction.confidence,
                    source=GenerationApproach.PATTERN_LEARNING,
                    rationale=pattern_prediction.reasoning,
                    processing_time=time.time() - start_time,
                    metadata={
                        'pattern_used': pattern_prediction.pattern_used,
                        'similar_examples': pattern_prediction.similar_examples
                    }
                )
                
                candidates.append(candidate)
                
        except Exception as e:
            logger.debug(f"Pattern learning generation failed: {str(e)}")
        
        return candidates
    
    def _validate_candidates(self, candidates: List[NameCandidate], 
                           existing_names: List[str]) -> List[NameCandidate]:
        """Validate all candidates using BEM engine"""
        
        validated_candidates = []
        
        for candidate in candidates:
            # Validate BEM format
            validation_result = self.bem_engine.validate_bem_name(candidate.name)
            candidate.validation_result = validation_result
            
            # Check uniqueness
            is_unique = self.bem_engine.check_name_uniqueness(candidate.name, existing_names)
            
            if validation_result.is_valid and is_unique:
                # Boost confidence for valid names
                candidate.confidence = min(candidate.confidence + 0.1, 1.0)
                validated_candidates.append(candidate)
            elif validation_result.is_valid:
                # Valid but not unique - reduce confidence
                candidate.confidence *= 0.8
                candidate.rationale += " (name not unique)"
                validated_candidates.append(candidate)
            else:
                # Invalid BEM format - significantly reduce confidence
                candidate.confidence *= 0.3
                candidate.rationale += f" (invalid BEM: {validation_result.error_message})"
                validated_candidates.append(candidate)
        
        return validated_candidates
    
    def _deduplicate_and_rank_candidates(self, candidates: List[NameCandidate]) -> List[NameCandidate]:
        """Remove duplicates and rank candidates by confidence"""
        
        # Group by name and keep highest confidence
        name_to_candidate = {}
        
        for candidate in candidates:
            existing = name_to_candidate.get(candidate.name)
            
            if not existing or candidate.confidence > existing.confidence:
                name_to_candidate[candidate.name] = candidate
            elif candidate.confidence == existing.confidence:
                # Merge rationale for equal confidence
                existing.rationale += f" | {candidate.rationale}"
        
        # Sort by confidence (descending)
        unique_candidates = list(name_to_candidate.values())
        unique_candidates.sort(key=lambda c: c.confidence, reverse=True)
        
        return unique_candidates
    
    def _calculate_consensus_scores(self, candidates: List[NameCandidate]) -> Dict[str, float]:
        """Calculate consensus scores for candidates"""
        
        consensus_scores = {}
        
        # Group candidates by name
        name_groups = {}
        for candidate in candidates:
            if candidate.name not in name_groups:
                name_groups[candidate.name] = []
            name_groups[candidate.name].append(candidate)
        
        # Calculate consensus for each name
        for name, group in name_groups.items():
            # Base score from average confidence
            avg_confidence = sum(c.confidence for c in group) / len(group)
            
            # Boost for multiple approaches agreeing
            approach_count = len(set(c.source for c in group))
            approach_bonus = min(approach_count * 0.1, 0.3)
            
            # Boost for high-confidence approaches
            high_confidence_boost = sum(
                0.1 for c in group if c.confidence > 0.8
            )
            
            consensus_score = avg_confidence + approach_bonus + high_confidence_boost
            consensus_scores[name] = min(consensus_score, 1.0)
        
        return consensus_scores
    
    def _calculate_overall_consensus(self, candidates: List[NameCandidate]) -> float:
        """Calculate overall consensus score for the generation"""
        
        if not candidates:
            return 0.0
        
        # Check how many candidates have high confidence
        high_confidence_count = sum(1 for c in candidates if c.confidence > 0.7)
        high_confidence_ratio = high_confidence_count / len(candidates)
        
        # Check source diversity
        unique_sources = len(set(c.source for c in candidates))
        source_diversity = min(unique_sources / len(GenerationApproach), 1.0)
        
        # Check name convergence
        unique_names = len(set(c.name for c in candidates))
        name_convergence = 1.0 - (unique_names / len(candidates))
        
        # Combine factors
        consensus = (
            high_confidence_ratio * 0.5 +
            source_diversity * 0.3 +
            name_convergence * 0.2
        )
        
        return min(consensus, 1.0)
    
    async def _generate_result_explanation(self, field: FormField, context: FieldContext,
                                         selected_candidate: NameCandidate,
                                         all_candidates: List[NameCandidate]) -> str:
        """Generate comprehensive explanation for the result"""
        
        explanation_parts = []
        
        # Field description
        explanation_parts.append(
            f"Analyzed field '{field.name}' ({field.field_type.value if field.field_type else 'unknown'} type)"
        )
        
        # Context information
        if context.section_header:
            explanation_parts.append(f"Located in section: '{context.section_header}'")
        
        if context.label:
            explanation_parts.append(f"Field label: '{context.label}'")
        
        # Selection rationale
        explanation_parts.append(
            f"Selected '{selected_candidate.name}' from {selected_candidate.source.value} approach "
            f"with {selected_candidate.confidence:.2f} confidence"
        )
        
        # Alternative approaches
        if len(all_candidates) > 1:
            other_approaches = [c.source.value for c in all_candidates if c != selected_candidate]
            if other_approaches:
                explanation_parts.append(f"Also considered: {', '.join(set(other_approaches))}")
        
        # Detailed rationale
        explanation_parts.append(f"Rationale: {selected_candidate.rationale}")
        
        return '. '.join(explanation_parts) + '.'
    
    def _update_generation_stats(self, result: GenerationResult):
        """Update generation statistics"""
        
        self.generation_stats['total_generations'] += 1
        self.generation_stats['approach_usage'][result.approach_used.value] += 1
        
        # Update rolling averages
        total = self.generation_stats['total_generations']
        
        current_conf_avg = self.generation_stats['average_confidence']
        self.generation_stats['average_confidence'] = (
            (current_conf_avg * (total - 1) + result.selected_candidate.confidence) / total
        )
        
        current_time_avg = self.generation_stats['average_processing_time']
        self.generation_stats['average_processing_time'] = (
            (current_time_avg * (total - 1) + result.processing_time) / total
        )
        
        current_consensus_avg = self.generation_stats['consensus_rate']
        self.generation_stats['consensus_rate'] = (
            (current_consensus_avg * (total - 1) + result.consensus_score) / total
        )
    
    def explain_selection_rationale(self, selected: NameCandidate, 
                                  alternatives: List[NameCandidate]) -> str:
        """
        Generate detailed explanation for why a specific candidate was selected.
        
        Args:
            selected: The selected candidate
            alternatives: Alternative candidates that were considered
            
        Returns:
            Detailed rationale explanation
        """
        
        explanation_parts = []
        
        # Selection basis
        explanation_parts.append(
            f"Selected '{selected.name}' based on {selected.source.value} approach "
            f"with confidence score of {selected.confidence:.2f}"
        )
        
        # Validation status
        if selected.validation_result and selected.validation_result.is_valid:
            explanation_parts.append("Name follows proper BEM format")
        
        # Comparison with alternatives
        if alternatives:
            higher_confidence_alts = [a for a in alternatives if a.confidence > selected.confidence]
            if not higher_confidence_alts:
                explanation_parts.append("Had highest confidence among all candidates")
            else:
                explanation_parts.append("Selected despite lower confidence due to consensus factors")
        
        # Source-specific rationale
        explanation_parts.append(selected.rationale)
        
        # Alternative mentions
        if alternatives:
            alt_names = [a.name for a in alternatives[:2]]  # Top 2 alternatives
            if alt_names:
                explanation_parts.append(f"Alternatives considered: {', '.join(alt_names)}")
        
        return '. '.join(explanation_parts) + '.'
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive generation statistics"""
        
        stats = self.generation_stats.copy()
        
        # Add approach effectiveness
        total_gens = stats['total_generations']
        if total_gens > 0:
            approach_percentages = {
                approach: (count / total_gens) * 100
                for approach, count in stats['approach_usage'].items()
            }
            stats['approach_percentages'] = approach_percentages
        
        # Add component statistics
        if self.ai_analyzer:
            stats['ai_analyzer_stats'] = self.ai_analyzer.get_analysis_statistics()
        
        stats['pattern_learner_stats'] = self.pattern_learner.get_learning_statistics()
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources and save caches"""
        
        try:
            # Cleanup AI analyzer
            if self.ai_analyzer:
                await self.ai_analyzer.cleanup()
            
            # Save pattern learning data
            self.pattern_learner._save_learned_patterns()
            
            logger.info("Hybrid Name Generator cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {str(e)}")
    
    async def batch_generate_names(self, fields_with_context: List[Tuple[FormField, FieldContext]],
                                 existing_names: List[str] = None) -> List[GenerationResult]:
        """
        Generate names for multiple fields in batch.
        
        Args:
            fields_with_context: List of (field, context) tuples
            existing_names: List of existing field names
            
        Returns:
            List of GenerationResult objects
        """
        
        logger.info(f"Starting batch name generation for {len(fields_with_context)} fields")
        
        # Process fields concurrently (with reasonable limit)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
        existing_names = existing_names or []
        
        async def generate_with_semaphore(field_context_pair):
            async with semaphore:
                field, context = field_context_pair
                return await self.generate_complete_result(field, context, existing_names)
        
        # Execute all generations
        results = await asyncio.gather(
            *[generate_with_semaphore(pair) for pair in fields_with_context],
            return_exceptions=True
        )
        
        # Process results and handle exceptions
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch generation error: {str(result)}")
            else:
                successful_results.append(result)
                # Add generated name to existing names for uniqueness
                existing_names.append(result.selected_candidate.name)
        
        logger.info(f"Batch generation completed: {len(successful_results)} successful")
        
        return successful_results