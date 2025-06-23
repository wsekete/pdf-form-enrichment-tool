"""
AI Pattern Learning System

Enhances the existing training data system with machine learning capabilities.
This module learns from training data to identify patterns and improve BEM name
generation through intelligent pattern recognition and similarity matching.
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import joblib

from .data_loader import TrainingDataLoader, TrainingPattern, FieldContext
from .similarity_matcher import SimilarityMatcher
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PatternFeatures:
    """Features extracted from a training pattern"""
    context_words: List[str]
    bem_components: Dict[str, str]
    field_type: str
    section_type: str
    semantic_category: str
    confidence: float


@dataclass
class LearnedPattern:
    """A pattern learned from training data"""
    pattern_id: str
    template: str
    features: PatternFeatures
    frequency: int
    accuracy: float
    examples: List[str]
    confidence: float


@dataclass
class PatternPrediction:
    """Prediction result from pattern learning"""
    suggested_name: str
    confidence: float
    pattern_used: str
    similar_examples: List[str]
    reasoning: str


class AIPatternLearner:
    """
    Advanced pattern learning system that uses machine learning to identify
    and apply naming patterns from training data.
    
    Features:
    - TF-IDF vectorization for semantic similarity
    - Clustering to identify pattern groups
    - Frequency-based pattern weighting
    - Context-aware pattern matching
    - Continuous learning from new examples
    """
    
    def __init__(self, training_data_loader: TrainingDataLoader):
        self.training_loader = training_data_loader
        self.similarity_matcher = SimilarityMatcher()
        
        # Learning models
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        self.pattern_clusters = None
        self.learned_patterns = {}
        
        # Pattern database
        self.pattern_features = []
        self.pattern_templates = {}
        self.semantic_categories = {}
        
        # Model state
        self.is_trained = False
        self.model_version = "1.0"
        
        self._initialize_learning_system()
    
    def _initialize_learning_system(self):
        """Initialize the pattern learning system"""
        try:
            # Load existing model if available
            self._load_learned_patterns()
            
            # Train on current data if no model exists
            if not self.is_trained:
                self.train_on_existing_data()
                
            logger.info(f"AI Pattern Learner initialized with {len(self.learned_patterns)} patterns")
            
        except Exception as e:
            logger.warning(f"Failed to initialize pattern learner: {str(e)}")
            self.learned_patterns = {}
    
    def train_on_existing_data(self):
        """Train the pattern learning system on existing training data"""
        logger.info("Training AI pattern learner on existing data...")
        
        # Load all training data
        all_patterns = self.training_loader.load_all_training_data()
        if len(all_patterns) < 10:
            logger.warning("Insufficient training data for meaningful pattern learning")
            return
        
        # Extract features from all patterns
        self.pattern_features = [
            self._extract_pattern_features(pattern) 
            for pattern in all_patterns
        ]
        
        # Build TF-IDF vectors for context similarity
        context_texts = [
            ' '.join(features.context_words) 
            for features in self.pattern_features
        ]
        
        if context_texts:
            self.vectorizer.fit(context_texts)
            
            # Cluster patterns to identify groups
            vectors = self.vectorizer.transform(context_texts)
            n_clusters = min(10, len(all_patterns) // 5)  # Reasonable cluster count
            
            if n_clusters > 1:
                self.pattern_clusters = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = self.pattern_clusters.fit_predict(vectors)
                
                # Build learned patterns from clusters
                self._build_learned_patterns_from_clusters(all_patterns, cluster_labels)
            
            self.is_trained = True
            self._save_learned_patterns()
            
            logger.info(f"Training completed: {len(self.learned_patterns)} patterns learned")
    
    def _extract_pattern_features(self, pattern: TrainingPattern) -> PatternFeatures:
        """Extract meaningful features from a training pattern"""
        
        # Extract context words
        context_words = []
        if pattern.context.nearby_text:
            for text in pattern.context.nearby_text:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
                context_words.extend(words)
        
        if pattern.context.label:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', pattern.context.label.lower())
            context_words.extend(words)
        
        # Parse BEM components
        bem_components = self._parse_bem_name(pattern.bem_name)
        
        # Determine semantic category
        semantic_category = self._classify_semantic_category(context_words, bem_components)
        
        # Determine section type
        section_type = self._classify_section_type(pattern.context)
        
        return PatternFeatures(
            context_words=list(set(context_words)),  # Remove duplicates
            bem_components=bem_components,
            field_type=pattern.context.field_type or "unknown",
            section_type=section_type,
            semantic_category=semantic_category,
            confidence=pattern.context.confidence
        )
    
    def _parse_bem_name(self, bem_name: str) -> Dict[str, str]:
        """Parse BEM name into components"""
        components = {}
        
        if '__' in bem_name:
            block_element, modifier = bem_name.split('__', 1)
            components['modifier'] = modifier
        else:
            block_element = bem_name
        
        if '_' in block_element:
            block, element = block_element.split('_', 1)
            components['block'] = block
            components['element'] = element
        else:
            components['block'] = block_element
        
        return components
    
    def _classify_semantic_category(self, context_words: List[str], 
                                  bem_components: Dict[str, str]) -> str:
        """Classify the semantic category of a field"""
        
        # Define semantic categories based on common patterns
        categories = {
            'personal_info': ['name', 'first', 'last', 'middle', 'initial', 'personal'],
            'contact': ['phone', 'email', 'address', 'contact', 'mail', 'telephone'],
            'financial': ['amount', 'price', 'cost', 'payment', 'money', 'dollar', 'financial'],
            'date_time': ['date', 'time', 'day', 'month', 'year', 'when', 'schedule'],
            'identification': ['id', 'number', 'ssn', 'license', 'identification', 'social'],
            'insurance': ['insurance', 'policy', 'coverage', 'claim', 'benefit'],
            'medical': ['medical', 'health', 'doctor', 'physician', 'treatment'],
            'vehicle': ['vehicle', 'car', 'auto', 'truck', 'driver', 'license'],
            'legal': ['signature', 'witness', 'legal', 'agreement', 'consent'],
            'employment': ['employer', 'job', 'work', 'occupation', 'company']
        }
        
        all_words = context_words + list(bem_components.values())
        
        for category, keywords in categories.items():
            if any(keyword in ' '.join(all_words).lower() for keyword in keywords):
                return category
        
        return 'general'
    
    def _classify_section_type(self, context: FieldContext) -> str:
        """Classify the section type based on context"""
        
        if context.section_header:
            header = context.section_header.lower()
            
            if any(word in header for word in ['owner', 'applicant', 'personal']):
                return 'owner_information'
            elif any(word in header for word in ['contact', 'address', 'phone']):
                return 'contact_information'
            elif any(word in header for word in ['payment', 'financial', 'money']):
                return 'payment_information'
            elif any(word in header for word in ['insurance', 'policy', 'coverage']):
                return 'insurance_information'
            elif any(word in header for word in ['vehicle', 'auto', 'car']):
                return 'vehicle_information'
            elif any(word in header for word in ['signature', 'sign', 'witness']):
                return 'signature_section'
        
        return 'general_section'
    
    def _build_learned_patterns_from_clusters(self, patterns: List[TrainingPattern], 
                                            cluster_labels: np.ndarray):
        """Build learned patterns from clustered training data"""
        
        # Group patterns by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append((patterns[i], self.pattern_features[i]))
        
        # Build learned pattern for each cluster
        for cluster_id, cluster_patterns in clusters.items():
            if len(cluster_patterns) >= 2:  # Require minimum patterns per cluster
                learned_pattern = self._create_learned_pattern_from_cluster(
                    cluster_id, cluster_patterns
                )
                if learned_pattern:
                    self.learned_patterns[learned_pattern.pattern_id] = learned_pattern
    
    def _create_learned_pattern_from_cluster(self, cluster_id: int, 
                                           cluster_patterns: List[Tuple[TrainingPattern, PatternFeatures]]) -> Optional[LearnedPattern]:
        """Create a learned pattern from a cluster of similar patterns"""
        
        patterns, features = zip(*cluster_patterns)
        
        # Find most common BEM structure
        bem_structures = [self._get_bem_structure(p.bem_name) for p in patterns]
        structure_counts = Counter(bem_structures)
        most_common_structure = structure_counts.most_common(1)[0][0]
        
        # Find most common semantic category
        categories = [f.semantic_category for f in features]
        category_counts = Counter(categories)
        most_common_category = category_counts.most_common(1)[0][0]
        
        # Calculate pattern confidence
        confidence = sum(f.confidence for f in features) / len(features)
        
        # Create template
        template = self._create_pattern_template(most_common_structure, most_common_category)
        
        # Calculate accuracy (how well template matches examples)
        accuracy = self._calculate_pattern_accuracy(template, patterns)
        
        pattern_id = f"cluster_{cluster_id}_{most_common_category}"
        
        return LearnedPattern(
            pattern_id=pattern_id,
            template=template,
            features=features[0],  # Use first as representative
            frequency=len(patterns),
            accuracy=accuracy,
            examples=[p.bem_name for p in patterns[:5]],  # Keep top 5 examples
            confidence=confidence
        )
    
    def _get_bem_structure(self, bem_name: str) -> str:
        """Get the structural pattern of a BEM name"""
        if '__' in bem_name:
            return "block_element__modifier"
        elif '_' in bem_name:
            return "block_element"
        else:
            return "block_only"
    
    def _create_pattern_template(self, structure: str, category: str) -> str:
        """Create a pattern template from structure and category"""
        templates = {
            ('block_element__modifier', 'personal_info'): "{section}_name__{type}",
            ('block_element__modifier', 'contact'): "{section}_contact__{type}",
            ('block_element__modifier', 'financial'): "{section}_amount__{type}",
            ('block_element__modifier', 'date_time'): "{section}_date__{type}",
            ('block_element__modifier', 'identification'): "{section}_id__{type}",
            ('block_element', 'personal_info'): "{section}_name",
            ('block_element', 'contact'): "{section}_contact",
            ('block_only', 'legal'): "{section}"
        }
        
        return templates.get((structure, category), "{section}_{element}__{modifier}")
    
    def _calculate_pattern_accuracy(self, template: str, patterns: List[TrainingPattern]) -> float:
        """Calculate how accurately a template represents the patterns"""
        
        # This is a simplified accuracy calculation
        # In practice, you might want to apply the template and see how close the results are
        matches = 0
        total = len(patterns)
        
        for pattern in patterns:
            structure = self._get_bem_structure(pattern.bem_name)
            if structure in template:
                matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def predict_bem_name(self, context: FieldContext, field_type: str) -> Optional[PatternPrediction]:
        """
        Predict BEM name using learned patterns.
        
        Args:
            context: Field context information
            field_type: Type of the field
            
        Returns:
            PatternPrediction with suggested name and confidence
        """
        if not self.is_trained or not self.learned_patterns:
            return None
        
        # Extract features from input
        input_features = self._extract_context_features(context, field_type)
        
        # Find best matching pattern
        best_match = self._find_best_matching_pattern(input_features)
        
        if not best_match:
            return None
        
        # Apply pattern to generate name
        suggested_name = self._apply_pattern(best_match, input_features)
        
        return PatternPrediction(
            suggested_name=suggested_name,
            confidence=best_match.confidence * 0.8,  # Slight reduction for prediction uncertainty
            pattern_used=best_match.pattern_id,
            similar_examples=best_match.examples,
            reasoning=f"Applied learned pattern '{best_match.pattern_id}' based on {best_match.frequency} training examples"
        )
    
    def _extract_context_features(self, context: FieldContext, field_type: str) -> PatternFeatures:
        """Extract features from input context"""
        
        context_words = []
        if context.nearby_text:
            for text in context.nearby_text:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
                context_words.extend(words)
        
        if context.label:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', context.label.lower())
            context_words.extend(words)
        
        semantic_category = self._classify_semantic_category(context_words, {})
        section_type = self._classify_section_type(context)
        
        return PatternFeatures(
            context_words=list(set(context_words)),
            bem_components={},
            field_type=field_type,
            section_type=section_type,
            semantic_category=semantic_category,
            confidence=context.confidence
        )
    
    def _find_best_matching_pattern(self, input_features: PatternFeatures) -> Optional[LearnedPattern]:
        """Find the best matching learned pattern for input features"""
        
        best_pattern = None
        best_score = 0.0
        
        for pattern in self.learned_patterns.values():
            score = self._calculate_pattern_similarity(input_features, pattern.features)
            
            # Weight by pattern frequency and accuracy
            weighted_score = score * (pattern.frequency / 10) * pattern.accuracy
            
            if weighted_score > best_score:
                best_score = weighted_score
                best_pattern = pattern
        
        # Only return if score meets minimum threshold
        return best_pattern if best_score > 0.3 else None
    
    def _calculate_pattern_similarity(self, input_features: PatternFeatures, 
                                    pattern_features: PatternFeatures) -> float:
        """Calculate similarity between input and pattern features"""
        
        similarity_score = 0.0
        
        # Semantic category match (high weight)
        if input_features.semantic_category == pattern_features.semantic_category:
            similarity_score += 0.4
        
        # Section type match (medium weight)
        if input_features.section_type == pattern_features.section_type:
            similarity_score += 0.2
        
        # Field type match (medium weight)
        if input_features.field_type == pattern_features.field_type:
            similarity_score += 0.2
        
        # Context words overlap (low weight but additive)
        if input_features.context_words and pattern_features.context_words:
            common_words = set(input_features.context_words) & set(pattern_features.context_words)
            total_words = set(input_features.context_words) | set(pattern_features.context_words)
            
            if total_words:
                word_similarity = len(common_words) / len(total_words)
                similarity_score += 0.2 * word_similarity
        
        return min(similarity_score, 1.0)
    
    def _apply_pattern(self, pattern: LearnedPattern, input_features: PatternFeatures) -> str:
        """Apply learned pattern to generate BEM name"""
        
        template = pattern.template
        
        # Extract components from input
        section = self._extract_section_name(input_features)
        element = self._extract_element_name(input_features)
        modifier = self._extract_modifier_name(input_features)
        
        # Apply template
        try:
            if '{section}' in template:
                template = template.replace('{section}', section)
            if '{element}' in template:
                template = template.replace('{element}', element)
            if '{modifier}' in template:
                template = template.replace('{modifier}', modifier)
            if '{type}' in template:
                template = template.replace('{type}', modifier)
            
            return template
        except Exception:
            # Fallback to simple structure
            return f"{section}_{element}__{modifier}"
    
    def _extract_section_name(self, features: PatternFeatures) -> str:
        """Extract section name from features"""
        if features.section_type != 'general_section':
            return features.section_type.replace('_', '-')
        
        # Try to infer from context words
        if 'owner' in features.context_words or 'applicant' in features.context_words:
            return 'owner-information'
        elif 'contact' in features.context_words:
            return 'contact-details'
        elif 'payment' in features.context_words:
            return 'payment-information'
        
        return 'general'
    
    def _extract_element_name(self, features: PatternFeatures) -> str:
        """Extract element name from features"""
        
        # Map semantic categories to common elements
        element_mapping = {
            'personal_info': 'name',
            'contact': 'contact',
            'financial': 'amount',
            'date_time': 'date',
            'identification': 'id',
            'legal': 'signature'
        }
        
        element = element_mapping.get(features.semantic_category, 'field')
        
        # Try to be more specific based on context words
        if 'phone' in features.context_words:
            return 'phone'
        elif 'email' in features.context_words:
            return 'email'
        elif 'address' in features.context_words:
            return 'address'
        elif 'date' in features.context_words:
            return 'date'
        
        return element
    
    def _extract_modifier_name(self, features: PatternFeatures) -> str:
        """Extract modifier name from features"""
        
        # Map field types to modifiers
        modifier_mapping = {
            'text': 'input',
            'checkbox': 'option',
            'radio': 'selection',
            'signature': 'field',
            'dropdown': 'choice'
        }
        
        return modifier_mapping.get(features.field_type, 'field')
    
    def learn_from_feedback(self, original_context: FieldContext, predicted_name: str, 
                          actual_name: str, feedback_score: float):
        """
        Learn from user feedback to improve pattern accuracy.
        
        Args:
            original_context: Original field context
            predicted_name: Name predicted by the system
            actual_name: Actual name chosen by user
            feedback_score: Score indicating quality (0.0-1.0)
        """
        
        if feedback_score > 0.8:
            # Good prediction - reinforce the pattern
            self._reinforce_pattern(original_context, actual_name)
        elif feedback_score < 0.3:
            # Poor prediction - create new pattern
            self._create_feedback_pattern(original_context, actual_name)
        
        # Save updated patterns
        self._save_learned_patterns()
    
    def _reinforce_pattern(self, context: FieldContext, bem_name: str):
        """Reinforce an existing pattern that worked well"""
        
        features = self._extract_context_features(context, context.field_type or "unknown")
        
        # Find matching pattern and increase its weight
        for pattern in self.learned_patterns.values():
            similarity = self._calculate_pattern_similarity(features, pattern.features)
            if similarity > 0.7:
                pattern.frequency += 1
                pattern.confidence = min(pattern.confidence + 0.05, 1.0)
                break
    
    def _create_feedback_pattern(self, context: FieldContext, bem_name: str):
        """Create new pattern from user feedback"""
        
        features = self._extract_context_features(context, context.field_type or "unknown")
        
        pattern_id = f"feedback_{len(self.learned_patterns)}"
        structure = self._get_bem_structure(bem_name)
        template = self._create_pattern_template(structure, features.semantic_category)
        
        feedback_pattern = LearnedPattern(
            pattern_id=pattern_id,
            template=template,
            features=features,
            frequency=1,
            accuracy=1.0,  # Assume perfect since it's user-approved
            examples=[bem_name],
            confidence=0.8
        )
        
        self.learned_patterns[pattern_id] = feedback_pattern
    
    def _save_learned_patterns(self):
        """Save learned patterns to disk"""
        try:
            cache_dir = Path("/tmp/pdf_form_editor/pattern_cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            patterns_file = cache_dir / "learned_patterns.json"
            
            # Convert patterns to serializable format
            serializable_patterns = {}
            for pid, pattern in self.learned_patterns.items():
                serializable_patterns[pid] = asdict(pattern)
            
            with open(patterns_file, 'w') as f:
                json.dump({
                    'patterns': serializable_patterns,
                    'model_version': self.model_version,
                    'is_trained': self.is_trained
                }, f, indent=2)
            
            # Save vectorizer if available
            if self.vectorizer:
                vectorizer_file = cache_dir / "vectorizer.joblib"
                joblib.dump(self.vectorizer, vectorizer_file)
            
            logger.debug("Learned patterns saved successfully")
            
        except Exception as e:
            logger.warning(f"Failed to save learned patterns: {str(e)}")
    
    def _load_learned_patterns(self):
        """Load learned patterns from disk"""
        try:
            cache_dir = Path("/tmp/pdf_form_editor/pattern_cache")
            patterns_file = cache_dir / "learned_patterns.json"
            
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                
                # Convert back to LearnedPattern objects
                for pid, pattern_data in data['patterns'].items():
                    # Reconstruct PatternFeatures
                    features_data = pattern_data['features']
                    features = PatternFeatures(**features_data)
                    
                    # Reconstruct LearnedPattern
                    pattern_data['features'] = features
                    self.learned_patterns[pid] = LearnedPattern(**pattern_data)
                
                self.model_version = data.get('model_version', '1.0')
                self.is_trained = data.get('is_trained', False)
                
                # Load vectorizer if available
                vectorizer_file = cache_dir / "vectorizer.joblib"
                if vectorizer_file.exists():
                    self.vectorizer = joblib.load(vectorizer_file)
                
                logger.debug(f"Loaded {len(self.learned_patterns)} learned patterns")
                
        except Exception as e:
            logger.warning(f"Failed to load learned patterns: {str(e)}")
            self.learned_patterns = {}
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics about the learning system"""
        
        if not self.learned_patterns:
            return {
                'total_patterns': 0,
                'is_trained': False,
                'model_version': self.model_version
            }
        
        patterns = list(self.learned_patterns.values())
        
        return {
            'total_patterns': len(patterns),
            'is_trained': self.is_trained,
            'model_version': self.model_version,
            'avg_confidence': sum(p.confidence for p in patterns) / len(patterns),
            'avg_frequency': sum(p.frequency for p in patterns) / len(patterns),
            'avg_accuracy': sum(p.accuracy for p in patterns) / len(patterns),
            'semantic_categories': list(set(p.features.semantic_category for p in patterns)),
            'pattern_types': Counter([p.features.semantic_category for p in patterns])
        }