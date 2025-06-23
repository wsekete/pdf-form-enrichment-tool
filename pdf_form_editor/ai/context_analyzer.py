"""
AI Context Analyzer

AI-powered context analysis for intelligent field naming using OpenAI GPT-4.
This module provides contextual understanding of PDF form fields and generates
intelligent BEM naming suggestions based on semantic analysis.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import os

from .openai_client import OpenAIClient, OpenAIConfig, AIResponse, OpenAIModel
from ..core.field_extractor import FormField, FieldType  
from ..training.data_loader import FieldContext, TrainingDataLoader
from ..training.ai_pattern_learner import AIPatternLearner, PatternPrediction
from ..utils.logging import get_logger
from ..utils.errors import AIIntegrationError

logger = get_logger(__name__)


@dataclass
class ContextAnalysisResult:
    """Result of AI context analysis"""
    field_id: str
    semantic_understanding: Dict[str, Any]
    bem_suggestions: List[Dict[str, Any]]
    confidence: float
    reasoning: str
    processing_time: float
    ai_model_used: str
    error: Optional[str] = None


@dataclass
class BatchAnalysisResult:
    """Result of batch context analysis"""
    total_fields: int
    successful_analyses: int
    failed_analyses: int
    average_confidence: float
    total_processing_time: float
    results: List[ContextAnalysisResult]


class AIContextAnalyzer:
    """
    AI-powered context analyzer that uses OpenAI GPT-4 for intelligent field analysis.
    
    This class implements the complete AI-powered context analysis system as specified
    in the original task list. It provides:
    
    - Contextual field understanding using GPT-4
    - Intelligent BEM name generation 
    - Batch processing for efficiency
    - Response caching to minimize API costs
    - Confidence scoring and explanation generation
    - Fallback mechanisms for API failures
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True):
        """
        Initialize AI Context Analyzer.
        
        Args:
            api_key: OpenAI API key (if None, reads from environment)
            cache_enabled: Whether to enable response caching
        """
        
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise AIIntegrationError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        
        # Initialize OpenAI client
        self.config = OpenAIConfig(
            api_key=api_key,
            model=OpenAIModel.GPT_4,
            max_tokens=200,
            temperature=0.1,
            cache_enabled=cache_enabled,
            cache_ttl_hours=24,
            fallback_enabled=True
        )
        
        self.openai_client = OpenAIClient(self.config)
        
        # Initialize training data and pattern learning
        self.training_loader = TrainingDataLoader()
        self.pattern_learner = AIPatternLearner(self.training_loader)
        
        # Analysis statistics
        self.analysis_stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'cache_hits': 0,
            'average_confidence': 0.0,
            'total_api_calls': 0
        }
        
        logger.info("AI Context Analyzer initialized successfully")
    
    async def analyze_field_context(self, field: FormField, context: FieldContext) -> ContextAnalysisResult:
        """
        Analyze field context using AI to generate intelligent naming suggestions.
        
        Args:
            field: Form field to analyze
            context: Extracted context information
            
        Returns:
            ContextAnalysisResult with AI analysis and suggestions
        """
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get relevant training examples for context
            training_examples = self._get_relevant_training_examples(field, context)
            
            # Perform AI context analysis
            ai_response = await self.openai_client.analyze_field_context(
                field_name=field.name,
                context_data=self._prepare_context_data(field, context),
                training_examples=training_examples
            )
            
            # Parse AI response
            semantic_understanding = self._parse_semantic_analysis(ai_response.content)
            
            # Generate BEM suggestions using AI
            bem_suggestions = await self._generate_bem_suggestions(
                field, context, semantic_understanding, training_examples
            )
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(
                ai_response.confidence, 
                semantic_understanding.get('confidence', 0.0),
                len(bem_suggestions)
            )
            
            # Generate reasoning explanation
            reasoning = await self._generate_analysis_reasoning(
                field, context, semantic_understanding, bem_suggestions
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            result = ContextAnalysisResult(
                field_id=field.id,
                semantic_understanding=semantic_understanding,
                bem_suggestions=bem_suggestions,
                confidence=overall_confidence,
                reasoning=reasoning,
                processing_time=processing_time,
                ai_model_used=ai_response.model_used
            )
            
            # Update statistics
            self._update_analysis_stats(result, ai_response.cached)
            
            logger.debug(f"AI analysis completed for field {field.id} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.error(f"AI analysis failed for field {field.id}: {str(e)}")
            
            # Return error result with fallback
            return ContextAnalysisResult(
                field_id=field.id,
                semantic_understanding={},
                bem_suggestions=self._generate_fallback_suggestions(field, context),
                confidence=0.3,
                reasoning=f"AI analysis failed: {str(e)}. Using fallback suggestions.",
                processing_time=processing_time,
                ai_model_used="fallback",
                error=str(e)
            )
    
    async def batch_analyze_fields(self, fields_with_context: List[Tuple[FormField, FieldContext]]) -> BatchAnalysisResult:
        """
        Analyze multiple fields in batch for efficiency.
        
        Args:
            fields_with_context: List of (field, context) tuples
            
        Returns:
            BatchAnalysisResult with all analysis results
        """
        
        logger.info(f"Starting batch analysis of {len(fields_with_context)} fields")
        start_time = asyncio.get_event_loop().time()
        
        # Process fields concurrently (with reasonable limit)
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        async def analyze_with_semaphore(field_context_pair):
            async with semaphore:
                field, context = field_context_pair
                return await self.analyze_field_context(field, context)
        
        # Execute all analyses
        results = await asyncio.gather(
            *[analyze_with_semaphore(pair) for pair in fields_with_context],
            return_exceptions=True
        )
        
        # Process results and handle exceptions
        successful_results = []
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"Batch analysis error: {str(result)}")
            else:
                successful_results.append(result)
                if result.error:
                    failed_count += 1
        
        total_processing_time = asyncio.get_event_loop().time() - start_time
        
        # Calculate statistics
        avg_confidence = (
            sum(r.confidence for r in successful_results) / len(successful_results)
            if successful_results else 0.0
        )
        
        batch_result = BatchAnalysisResult(
            total_fields=len(fields_with_context),
            successful_analyses=len(successful_results) - failed_count,
            failed_analyses=failed_count,
            average_confidence=avg_confidence,
            total_processing_time=total_processing_time,
            results=successful_results
        )
        
        logger.info(
            f"Batch analysis completed: {batch_result.successful_analyses}/{batch_result.total_fields} "
            f"successful in {total_processing_time:.2f}s"
        )
        
        return batch_result
    
    async def explain_naming_decision(self, field: FormField, chosen_name: str, 
                                   analysis_result: ContextAnalysisResult) -> str:
        """
        Generate detailed explanation for a naming decision.
        
        Args:
            field: Original form field
            chosen_name: Selected BEM name
            analysis_result: Previous analysis result
            
        Returns:
            Detailed explanation string
        """
        
        context_data = {
            'original_name': field.name,
            'chosen_name': chosen_name,
            'field_type': field.field_type.value if field.field_type else 'unknown',
            'semantic_analysis': analysis_result.semantic_understanding,
            'ai_confidence': analysis_result.confidence
        }
        
        try:
            ai_response = await self.openai_client.explain_naming_decision(
                field_name=field.name,
                chosen_name=chosen_name,
                context=context_data
            )
            
            return ai_response.content
            
        except Exception as e:
            logger.warning(f"Failed to generate AI explanation: {str(e)}")
            return self._generate_fallback_explanation(field, chosen_name, analysis_result)
    
    def _get_relevant_training_examples(self, field: FormField, context: FieldContext) -> List[str]:
        """Get relevant training examples for the field context"""
        
        try:
            # Use pattern learner to find similar examples
            prediction = self.pattern_learner.predict_bem_name(context, field.field_type.value if field.field_type else "unknown")
            
            if prediction and prediction.similar_examples:
                return prediction.similar_examples[:5]  # Top 5 examples
                
        except Exception as e:
            logger.debug(f"Failed to get training examples: {str(e)}")
        
        # Fallback: get examples from training loader
        try:
            all_patterns = self.training_loader.load_all_training_data()
            
            # Find patterns with similar context
            similar_patterns = []
            for pattern in all_patterns:
                if self._is_context_similar(context, pattern.context):
                    similar_patterns.append(pattern.bem_name)
                    if len(similar_patterns) >= 5:
                        break
            
            return similar_patterns
            
        except Exception as e:
            logger.debug(f"Failed to load training examples: {str(e)}")
            return []
    
    def _is_context_similar(self, context1: FieldContext, context2: FieldContext) -> bool:
        """Check if two contexts are similar"""
        
        # Simple similarity based on common words
        if context1.label and context2.label:
            words1 = set(context1.label.lower().split())
            words2 = set(context2.label.lower().split())
            common_words = words1 & words2
            
            if len(common_words) > 0:
                return True
        
        # Check section headers
        if context1.section_header and context2.section_header:
            if context1.section_header.lower() in context2.section_header.lower():
                return True
        
        return False
    
    def _prepare_context_data(self, field: FormField, context: FieldContext) -> Dict[str, Any]:
        """Prepare context data for AI analysis"""
        
        return {
            'field_id': field.id,
            'field_name': field.name,
            'field_type': field.field_type.value if field.field_type else 'unknown',
            'page_number': field.page,
            'coordinates': field.rect,
            'section_header': context.section_header,
            'nearby_text': context.nearby_text,
            'label': context.label,
            'visual_group': context.visual_group,
            'confidence': context.confidence,
            'parent_field': field.parent_field_id
        }
    
    def _parse_semantic_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into semantic understanding"""
        
        try:
            # Try to parse as JSON
            parsed = json.loads(ai_response)
            return parsed
            
        except json.JSONDecodeError:
            # Fallback: extract information from text
            logger.debug("Failed to parse AI response as JSON, using text extraction")
            
            lines = ai_response.strip().split('\n')
            result = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    # Try to convert to appropriate type
                    if value.replace('.', '').isdigit():
                        value = float(value)
                    elif value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    
                    result[key] = value
            
            return result
    
    async def _generate_bem_suggestions(self, field: FormField, context: FieldContext, 
                                      semantic_understanding: Dict[str, Any], 
                                      training_examples: List[str]) -> List[Dict[str, Any]]:
        """Generate BEM suggestions using AI and pattern learning"""
        
        suggestions = []
        
        # Get AI-based suggestions
        try:
            ai_response = await self.openai_client.generate_bem_name(
                field_analysis=semantic_understanding,
                training_patterns=training_examples
            )
            
            ai_suggestions = self._parse_bem_suggestions(ai_response.content)
            suggestions.extend(ai_suggestions)
            
        except Exception as e:
            logger.debug(f"AI BEM generation failed: {str(e)}")
        
        # Get pattern learner suggestions
        try:
            pattern_prediction = self.pattern_learner.predict_bem_name(
                context, field.field_type.value if field.field_type else "unknown"
            )
            
            if pattern_prediction:
                suggestions.append({
                    'name': pattern_prediction.suggested_name,
                    'confidence': pattern_prediction.confidence,
                    'source': 'pattern_learning',
                    'reasoning': pattern_prediction.reasoning
                })
                
        except Exception as e:
            logger.debug(f"Pattern learning failed: {str(e)}")
        
        # Ensure we have at least one suggestion
        if not suggestions:
            suggestions = self._generate_fallback_suggestions(field, context)
        
        # Sort by confidence and return top suggestions
        suggestions.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
        return suggestions[:3]  # Return top 3 suggestions
    
    def _parse_bem_suggestions(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI BEM suggestions from response"""
        
        try:
            # Try to parse as JSON
            parsed = json.loads(ai_response)
            
            suggestions = []
            
            # Handle different response formats
            if 'primary' in parsed:
                # Format: {"primary": {...}, "alternatives": [...]}
                primary = parsed['primary']
                suggestions.append({
                    'name': primary['name'],
                    'confidence': primary['confidence'],
                    'source': 'ai_primary',
                    'reasoning': parsed.get('reasoning', 'AI-generated primary suggestion')
                })
                
                for alt in parsed.get('alternatives', []):
                    suggestions.append({
                        'name': alt['name'],
                        'confidence': alt['confidence'],
                        'source': 'ai_alternative',
                        'reasoning': 'AI-generated alternative'
                    })
            
            elif isinstance(parsed, list):
                # Format: [{"name": ..., "confidence": ...}, ...]
                for item in parsed:
                    suggestions.append({
                        'name': item['name'],
                        'confidence': item.get('confidence', 0.7),
                        'source': 'ai_generated',
                        'reasoning': item.get('reasoning', 'AI-generated suggestion')
                    })
            
            return suggestions
            
        except json.JSONDecodeError:
            # Fallback: extract names from text
            lines = ai_response.strip().split('\n')
            suggestions = []
            
            for line in lines:
                # Look for BEM-like patterns
                if '_' in line and '__' in line:
                    # Extract the BEM name
                    words = line.split()
                    for word in words:
                        if '_' in word and '__' in word:
                            suggestions.append({
                                'name': word,
                                'confidence': 0.6,
                                'source': 'ai_extracted',
                                'reasoning': 'Extracted from AI text response'
                            })
                            break
            
            return suggestions
    
    def _generate_fallback_suggestions(self, field: FormField, context: FieldContext) -> List[Dict[str, Any]]:
        """Generate fallback suggestions when AI fails"""
        
        # Simple rule-based fallback
        section = 'general'
        element = 'field'
        modifier = 'input'
        
        if context.section_header:
            section = context.section_header.lower().replace(' ', '-')
        
        if context.label:
            element = context.label.lower().replace(' ', '-')
        elif field.name and not field.name.startswith(('field', 'text')):
            element = field.name.lower().replace(' ', '-')
        
        if field.field_type:
            type_modifiers = {
                FieldType.TEXT: 'input',
                FieldType.CHECKBOX: 'option',
                FieldType.RADIO: 'selection',
                FieldType.SIGNATURE: 'field',
                FieldType.DROPDOWN: 'choice'
            }
            modifier = type_modifiers.get(field.field_type, 'field')
        
        fallback_name = f"{section}_{element}__{modifier}"
        
        return [{
            'name': fallback_name,
            'confidence': 0.3,
            'source': 'fallback',
            'reasoning': 'Fallback suggestion due to AI analysis failure'
        }]
    
    def _calculate_overall_confidence(self, ai_confidence: float, 
                                    semantic_confidence: float, 
                                    suggestion_count: int) -> float:
        """Calculate overall confidence score"""
        
        # Base confidence from AI
        confidence = ai_confidence * 0.7
        
        # Boost from semantic understanding
        confidence += semantic_confidence * 0.2
        
        # Boost from multiple suggestions
        if suggestion_count > 1:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _generate_analysis_reasoning(self, field: FormField, context: FieldContext,
                                         semantic_understanding: Dict[str, Any],
                                         bem_suggestions: List[Dict[str, Any]]) -> str:
        """Generate reasoning explanation for the analysis"""
        
        try:
            reasoning_context = {
                'field_name': field.name,
                'semantic_analysis': semantic_understanding,
                'suggestion_count': len(bem_suggestions),
                'top_suggestion': bem_suggestions[0] if bem_suggestions else None
            }
            
            ai_response = await self.openai_client.explain_naming_decision(
                field_name=field.name,
                chosen_name=bem_suggestions[0]['name'] if bem_suggestions else 'unknown',
                context=reasoning_context
            )
            
            return ai_response.content
            
        except Exception as e:
            logger.debug(f"Failed to generate AI reasoning: {str(e)}")
            return self._generate_fallback_reasoning(field, context, semantic_understanding, bem_suggestions)
    
    def _generate_fallback_reasoning(self, field: FormField, context: FieldContext,
                                   semantic_understanding: Dict[str, Any],
                                   bem_suggestions: List[Dict[str, Any]]) -> str:
        """Generate fallback reasoning when AI fails"""
        
        reasoning_parts = []
        
        # Field identification
        reasoning_parts.append(f"Analyzed field '{field.name}' of type {field.field_type.value if field.field_type else 'unknown'}")
        
        # Context information
        if context.section_header:
            reasoning_parts.append(f"Located in section: {context.section_header}")
        
        if context.label:
            reasoning_parts.append(f"Field label: {context.label}")
        
        # Semantic understanding
        if semantic_understanding:
            section = semantic_understanding.get('section', 'unknown')
            element = semantic_understanding.get('element', 'unknown') 
            reasoning_parts.append(f"Classified as {section} section, {element} element")
        
        # Suggestions
        if bem_suggestions:
            top_suggestion = bem_suggestions[0]
            reasoning_parts.append(f"Top suggestion: {top_suggestion['name']} (confidence: {top_suggestion['confidence']:.2f})")
        
        return '. '.join(reasoning_parts) + '.'
    
    def _generate_fallback_explanation(self, field: FormField, chosen_name: str, 
                                     analysis_result: ContextAnalysisResult) -> str:
        """Generate fallback explanation when AI fails"""
        
        return (
            f"Selected '{chosen_name}' for field '{field.name}' based on analysis. "
            f"The field appears to be a {field.field_type.value if field.field_type else 'unknown'} type field "
            f"with confidence score of {analysis_result.confidence:.2f}. "
            f"This BEM name follows the standard block_element__modifier convention."
        )
    
    def _update_analysis_stats(self, result: ContextAnalysisResult, was_cached: bool):
        """Update analysis statistics"""
        
        self.analysis_stats['total_analyses'] += 1
        
        if not result.error:
            self.analysis_stats['successful_analyses'] += 1
        
        if was_cached:
            self.analysis_stats['cache_hits'] += 1
        else:
            self.analysis_stats['total_api_calls'] += 1
        
        # Update average confidence (rolling average)
        current_avg = self.analysis_stats['average_confidence']
        total = self.analysis_stats['total_analyses']
        
        self.analysis_stats['average_confidence'] = (
            (current_avg * (total - 1) + result.confidence) / total
        )
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get comprehensive analysis statistics"""
        
        stats = self.analysis_stats.copy()
        
        # Add OpenAI client statistics
        openai_stats = self.openai_client.get_usage_statistics()
        stats.update({
            'openai_requests': openai_stats['total_requests'],
            'openai_cache_hit_rate': openai_stats['cache_hit_rate'],
            'openai_cache_size_mb': openai_stats['cache_size_mb']
        })
        
        # Add pattern learning statistics
        pattern_stats = self.pattern_learner.get_learning_statistics()
        stats.update({
            'learned_patterns': pattern_stats['total_patterns'],
            'pattern_learning_trained': pattern_stats['is_trained']
        })
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources and save caches"""
        
        try:
            # Save OpenAI cache
            self.openai_client.cleanup_cache()
            
            # Save pattern learning data
            self.pattern_learner._save_learned_patterns()
            
            logger.info("AI Context Analyzer cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {str(e)}")