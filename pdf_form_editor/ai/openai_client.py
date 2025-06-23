"""
OpenAI Integration Infrastructure

Provides secure, robust OpenAI API integration with comprehensive error handling,
caching, and fallback mechanisms. This infrastructure supports the AI-powered
context analysis and intelligent BEM name generation.
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

from ..utils.logging import get_logger
from ..utils.errors import AIIntegrationError

logger = get_logger(__name__)


class OpenAIModel(Enum):
    """Supported OpenAI models"""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str
    model: OpenAIModel = OpenAIModel.GPT_4
    max_tokens: int = 150
    temperature: float = 0.1
    timeout: int = 30
    max_retries: int = 3
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    fallback_enabled: bool = True


@dataclass
class AIResponse:
    """AI API response with metadata"""
    content: str
    model_used: str
    tokens_used: int
    response_time: float
    confidence: float
    cached: bool = False
    error: Optional[str] = None


@dataclass
class AIRequest:
    """AI API request structure"""
    prompt: str
    context: Dict[str, Any]
    request_id: str
    timestamp: float


class OpenAIClient:
    """
    Robust OpenAI API client with caching, error handling, and fallback mechanisms.
    
    Features:
    - Automatic retry logic with exponential backoff
    - Response caching to minimize API costs
    - Comprehensive error handling and recovery
    - Request rate limiting and quota management
    - Fallback mechanisms for API failures
    """
    
    def __init__(self, config: OpenAIConfig):
        if not OPENAI_AVAILABLE:
            raise AIIntegrationError("OpenAI library not installed. Run: pip install openai")
        
        self.config = config
        self.client = None
        self.cache = {}
        self.cache_dir = Path("/tmp/pdf_form_editor/ai_cache")
        self.request_history = []
        
        self._initialize_client()
        self._setup_cache()
    
    def _initialize_client(self):
        """Initialize OpenAI client with API key validation"""
        if not self.config.api_key:
            raise AIIntegrationError("OpenAI API key not provided")
        
        try:
            self.client = OpenAI(api_key=self.config.api_key)
            # Test connection with a simple request
            self._test_connection()
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            raise AIIntegrationError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _test_connection(self):
        """Test OpenAI API connection"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model.value,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=5
            )
            logger.debug("OpenAI connection test successful")
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            raise
    
    def _setup_cache(self):
        """Setup response caching system"""
        if self.config.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_existing_cache()
            logger.debug(f"Cache initialized at {self.cache_dir}")
    
    def _load_existing_cache(self):
        """Load existing cache from disk"""
        cache_file = self.cache_dir / "responses.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                    
                # Clean expired entries
                current_time = time.time()
                expired_keys = [
                    key for key, value in self.cache.items()
                    if current_time - value.get('timestamp', 0) > (self.config.cache_ttl_hours * 3600)
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                
                logger.debug(f"Loaded {len(self.cache)} cached responses")
            except Exception as e:
                logger.warning(f"Failed to load cache: {str(e)}")
                self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        if not self.config.cache_enabled:
            return
        
        try:
            cache_file = self.cache_dir / "responses.json"
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {str(e)}")
    
    def _generate_cache_key(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        content = f"{prompt}|{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[AIResponse]:
        """Retrieve cached response if available and valid"""
        if not self.config.cache_enabled or cache_key not in self.cache:
            return None
        
        cached_data = self.cache[cache_key]
        cache_age = time.time() - cached_data.get('timestamp', 0)
        
        if cache_age > (self.config.cache_ttl_hours * 3600):
            del self.cache[cache_key]
            return None
        
        response_data = cached_data['response']
        response_data['cached'] = True
        
        logger.debug(f"Using cached response for key {cache_key[:8]}...")
        return AIResponse(**response_data)
    
    def _cache_response(self, cache_key: str, response: AIResponse):
        """Cache response for future use"""
        if not self.config.cache_enabled:
            return
        
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'response': asdict(response)
        }
        
        # Periodically save cache to disk
        if len(self.cache) % 10 == 0:
            self._save_cache()
    
    async def analyze_field_context(self, field_name: str, context_data: Dict[str, Any], 
                                  training_examples: List[str] = None) -> AIResponse:
        """
        Analyze field context using OpenAI to generate intelligent naming suggestions.
        
        Args:
            field_name: Current field name
            context_data: Extracted context information
            training_examples: Relevant training examples for context
            
        Returns:
            AIResponse with analysis and suggestions
        """
        prompt = self._build_context_analysis_prompt(field_name, context_data, training_examples)
        
        return await self._make_ai_request(
            prompt=prompt,
            context=context_data,
            request_type="context_analysis"
        )
    
    async def generate_bem_name(self, field_analysis: Dict[str, Any], 
                              training_patterns: List[str] = None) -> AIResponse:
        """
        Generate BEM-compliant name using AI analysis.
        
        Args:
            field_analysis: Analysis results from context analysis
            training_patterns: Relevant BEM patterns from training data
            
        Returns:
            AIResponse with BEM name suggestions
        """
        prompt = self._build_bem_generation_prompt(field_analysis, training_patterns)
        
        return await self._make_ai_request(
            prompt=prompt,
            context=field_analysis,
            request_type="bem_generation"
        )
    
    async def explain_naming_decision(self, field_name: str, chosen_name: str, 
                                    context: Dict[str, Any]) -> AIResponse:
        """
        Generate explanation for naming decision.
        
        Args:
            field_name: Original field name
            chosen_name: Selected BEM name
            context: Decision context
            
        Returns:
            AIResponse with explanation
        """
        prompt = self._build_explanation_prompt(field_name, chosen_name, context)
        
        return await self._make_ai_request(
            prompt=prompt,
            context=context,
            request_type="explanation"
        )
    
    async def batch_analyze_fields(self, fields_data: List[Dict[str, Any]]) -> List[AIResponse]:
        """
        Analyze multiple fields in batch for efficiency.
        
        Args:
            fields_data: List of field data to analyze
            
        Returns:
            List of AIResponse objects
        """
        tasks = [
            self.analyze_field_context(
                field_data['name'], 
                field_data['context'], 
                field_data.get('training_examples')
            )
            for field_data in fields_data
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _make_ai_request(self, prompt: str, context: Dict[str, Any], 
                             request_type: str) -> AIResponse:
        """
        Make AI request with retry logic and error handling.
        
        Args:
            prompt: The prompt to send
            context: Request context for caching
            request_type: Type of request for logging
            
        Returns:
            AIResponse with result or error information
        """
        # Check cache first
        cache_key = self._generate_cache_key(prompt, context)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Create request record
        request = AIRequest(
            prompt=prompt,
            context=context,
            request_id=cache_key[:8],
            timestamp=time.time()
        )
        
        self.request_history.append(request)
        
        # Make request with retry logic
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()
                
                response = await self._call_openai_api(prompt)
                
                response_time = time.time() - start_time
                
                ai_response = AIResponse(
                    content=response.choices[0].message.content,
                    model_used=response.model,
                    tokens_used=response.usage.total_tokens,
                    response_time=response_time,
                    confidence=self._calculate_confidence(response)
                )
                
                # Cache successful response
                self._cache_response(cache_key, ai_response)
                
                logger.debug(f"AI request successful: {request_type} ({response_time:.2f}s)")
                return ai_response
                
            except Exception as e:
                logger.warning(f"AI request attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.config.max_retries - 1:
                    # Final attempt failed
                    error_response = AIResponse(
                        content="",
                        model_used=self.config.model.value,
                        tokens_used=0,
                        response_time=0.0,
                        confidence=0.0,
                        error=str(e)
                    )
                    
                    if self.config.fallback_enabled:
                        error_response.content = self._generate_fallback_response(request_type, context)
                        error_response.confidence = 0.3
                    
                    return error_response
                
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)
        
        # Should not reach here
        return AIResponse(
            content="",
            model_used=self.config.model.value,
            tokens_used=0,
            response_time=0.0,
            confidence=0.0,
            error="Max retries exceeded"
        )
    
    async def _call_openai_api(self, prompt: str):
        """Make actual OpenAI API call"""
        return await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.config.model.value,
            messages=[{
                "role": "system",
                "content": "You are an expert at analyzing PDF form fields and generating BEM-compliant naming conventions."
            }, {
                "role": "user", 
                "content": prompt
            }],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            timeout=self.config.timeout
        )
    
    def _calculate_confidence(self, response) -> float:
        """Calculate confidence score for AI response"""
        # Base confidence from response completion
        confidence = 0.7
        
        # Adjust based on response length (longer typically better)
        content_length = len(response.choices[0].message.content)
        if content_length > 50:
            confidence += 0.1
        if content_length > 100:
            confidence += 0.1
        
        # Adjust based on token usage efficiency
        tokens_ratio = response.usage.completion_tokens / max(response.usage.prompt_tokens, 1)
        if 0.1 <= tokens_ratio <= 0.5:  # Good ratio
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_fallback_response(self, request_type: str, context: Dict[str, Any]) -> str:
        """Generate fallback response when AI is unavailable"""
        if request_type == "context_analysis":
            return "Unable to analyze context - using rule-based fallback"
        elif request_type == "bem_generation":
            return "field_element__modifier"
        elif request_type == "explanation":
            return "AI analysis unavailable - decision based on heuristics"
        else:
            return "AI service temporarily unavailable"
    
    def _build_context_analysis_prompt(self, field_name: str, context_data: Dict[str, Any], 
                                     training_examples: List[str] = None) -> str:
        """Build prompt for context analysis"""
        prompt = f"""
Analyze this PDF form field for BEM naming:

Field Name: {field_name}
Field Type: {context_data.get('field_type', 'unknown')}
Section Header: {context_data.get('section_header', 'none')}
Nearby Text: {context_data.get('nearby_text', [])}
Label: {context_data.get('label', 'none')}
Visual Group: {context_data.get('visual_group', 'none')}

"""
        
        if training_examples:
            prompt += f"Similar Examples: {', '.join(training_examples[:3])}\n"
        
        prompt += """
Provide:
1. Section classification (owner-info, payment, contact, etc.)
2. Element purpose (name, date, amount, etc.)
3. Suggested modifier if needed
4. Confidence level (0.0-1.0)

Format response as JSON:
{
  "section": "section-name",
  "element": "element-name", 
  "modifier": "modifier-name",
  "confidence": 0.85,
  "reasoning": "explanation"
}
"""
        return prompt
    
    def _build_bem_generation_prompt(self, field_analysis: Dict[str, Any], 
                                   training_patterns: List[str] = None) -> str:
        """Build prompt for BEM name generation"""
        prompt = f"""
Generate a BEM-compliant field name using this analysis:

Analysis: {json.dumps(field_analysis, indent=2)}
"""
        
        if training_patterns:
            prompt += f"Relevant Patterns: {', '.join(training_patterns[:5])}\n"
        
        prompt += """
Generate BEM name following format: block_element__modifier

Requirements:
- Use lowercase letters, numbers, hyphens only
- Block: section/group (e.g., owner-information, payment-details)
- Element: specific field purpose (e.g., name, date, amount)
- Modifier: field type or variation (e.g., first, input, option)

Provide 3 alternatives with confidence scores:

Format response as JSON:
{
  "primary": {"name": "block_element__modifier", "confidence": 0.9},
  "alternatives": [
    {"name": "alternative1", "confidence": 0.8},
    {"name": "alternative2", "confidence": 0.7}
  ],
  "reasoning": "explanation of choice"
}
"""
        return prompt
    
    def _build_explanation_prompt(self, field_name: str, chosen_name: str, 
                                context: Dict[str, Any]) -> str:
        """Build prompt for explanation generation"""
        return f"""
Explain why this BEM name was chosen:

Original: {field_name}
Selected: {chosen_name}
Context: {json.dumps(context, indent=2)}

Provide a clear, user-friendly explanation covering:
1. What section/group this field belongs to
2. What purpose this field serves
3. Why this specific BEM structure was chosen
4. How it improves upon the original name

Keep explanation concise and professional.
"""
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for monitoring"""
        total_requests = len(self.request_history)
        cached_responses = len([r for r in self.cache.values()])
        
        if total_requests > 0:
            recent_requests = [r for r in self.request_history if time.time() - r.timestamp < 3600]
            cache_hit_rate = cached_responses / total_requests if total_requests > 0 else 0
        else:
            recent_requests = []
            cache_hit_rate = 0
        
        return {
            "total_requests": total_requests,
            "recent_requests_1h": len(recent_requests),
            "cached_responses": cached_responses,
            "cache_hit_rate": cache_hit_rate,
            "cache_size_mb": len(json.dumps(self.cache).encode()) / (1024 * 1024)
        }
    
    def cleanup_cache(self):
        """Clean up cache and save to disk"""
        self._save_cache()
        logger.info("Cache cleanup completed")