"""Pattern analysis engine for extracting BEM naming patterns."""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from ..core.field_extractor import FormField, FieldContext
from .csv_schema import CSVFieldMapping, NamingPattern
import logging
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class ContextPattern:
    """Pattern linking field context to BEM naming."""
    trigger_text: List[str]  # Text that indicates this pattern
    bem_block: str  # Recommended block name
    bem_element: str  # Recommended element name
    confidence: float  # How often this pattern is successful
    examples: List[str] = field(default_factory=list)  # Sample BEM names using this pattern
    spatial_indicators: List[str] = field(default_factory=list)  # Spatial positioning clues


@dataclass
class SpatialPattern:
    """Pattern based on spatial positioning and layout."""
    position_range: Dict[str, Tuple[float, float]]  # x, y, width, height ranges
    typical_block: str  # Most common block name in this area
    field_sequence: List[str]  # Common element ordering
    confidence: float
    page_number: int = 1
    examples: List[str] = field(default_factory=list)


@dataclass
class PatternDatabase:
    """Searchable database of naming patterns."""
    context_patterns: List[ContextPattern] = field(default_factory=list)
    spatial_patterns: List[SpatialPattern] = field(default_factory=list)
    naming_patterns: List[NamingPattern] = field(default_factory=list)
    pattern_index: Dict[str, List[int]] = field(default_factory=dict)  # keyword -> pattern indices
    confidence_threshold: float = 0.5


@dataclass
class TrainingExample:
    """Training example from data loader."""
    pdf_fields: List[FormField]
    csv_mappings: List[CSVFieldMapping]
    field_correlations: Dict[str, str]
    context_data: List[FieldContext]
    confidence: float


@dataclass
class AnalysisReport:
    """Comprehensive analysis report of training data."""
    total_examples: int
    total_fields: int
    pattern_coverage: Dict[str, float]
    confidence_distribution: Dict[str, int]
    common_blocks: List[str]
    common_elements: List[str]
    spatial_clusters: List[Dict[str, Any]]
    recommendations: List[str]


class PatternAnalyzer:
    """Analyze training data to extract BEM naming patterns."""
    
    def __init__(self):
        self.analyzed_examples = []
        self.pattern_database = PatternDatabase()
    
    def analyze_training_data(self, examples: List[TrainingExample]) -> PatternDatabase:
        """Comprehensive analysis of training examples."""
        logger.info(f"Analyzing {len(examples)} training examples")
        
        self.analyzed_examples = examples
        
        # Extract different types of patterns
        context_patterns = self.extract_context_patterns(examples)
        spatial_patterns = self.analyze_spatial_patterns(examples)
        
        # Build searchable database
        database = self.build_pattern_database(examples)
        database.context_patterns = context_patterns
        database.spatial_patterns = spatial_patterns
        
        self.pattern_database = database
        
        logger.info(f"Analysis complete: {len(context_patterns)} context patterns, "
                   f"{len(spatial_patterns)} spatial patterns")
        
        return database
    
    def extract_context_patterns(self, examples: List[TrainingExample]) -> List[ContextPattern]:
        """Correlate field context with successful BEM names."""
        logger.info("Extracting context patterns")
        
        # Group by BEM block-element combinations
        bem_contexts = defaultdict(list)
        
        for example in examples:
            for pdf_field in example.pdf_fields:
                field_id = pdf_field.field_id
                
                if field_id in example.field_correlations:
                    bem_name = example.field_correlations[field_id]
                    
                    # Find corresponding context
                    field_context = self._find_field_context(pdf_field, example.context_data)
                    if field_context:
                        bem_contexts[bem_name].append({
                            'context': field_context,
                            'field': pdf_field,
                            'example_id': id(example)
                        })
        
        # Analyze patterns for each BEM name
        patterns = []
        
        for bem_name, contexts in bem_contexts.items():
            if len(contexts) < 2:  # Need multiple examples for pattern
                continue
            
            pattern = self._analyze_bem_context_pattern(bem_name, contexts)
            if pattern and pattern.confidence >= 0.3:  # Minimum confidence threshold
                patterns.append(pattern)
        
        logger.info(f"Extracted {len(patterns)} context patterns")
        return patterns
    
    def _find_field_context(self, field: FormField, contexts: List[FieldContext]) -> Optional[FieldContext]:
        """Find context data for a specific field."""
        for context in contexts:
            if context.field_id == field.field_id:
                return context
        return None
    
    def _analyze_bem_context_pattern(self, bem_name: str, context_data: List[Dict]) -> Optional[ContextPattern]:
        """Analyze context pattern for a specific BEM name."""
        if len(context_data) < 2:
            return None
        
        # Parse BEM structure
        bem_parts = self._parse_bem_name(bem_name)
        if not bem_parts:
            return None
        
        block, element, modifier = bem_parts
        
        # Collect all text from contexts
        all_labels = []
        all_nearby_text = []
        spatial_indicators = []
        
        for ctx_info in context_data:
            context = ctx_info['context']
            field = ctx_info['field']
            
            if context.label_text:
                all_labels.append(context.label_text.lower())
            
            if context.nearby_text:
                all_nearby_text.extend([text.lower() for text in context.nearby_text])
            
            # Spatial indicators
            x, y = field.coordinates.get('x', 0), field.coordinates.get('y', 0)
            if x < 200:
                spatial_indicators.append('left_aligned')
            elif x > 400:
                spatial_indicators.append('right_aligned')
            
            if y < 200:
                spatial_indicators.append('top_section')
            elif y > 500:
                spatial_indicators.append('bottom_section')
        
        # Find common trigger words
        trigger_words = self._find_common_triggers(all_labels + all_nearby_text)
        
        # Calculate confidence based on consistency
        confidence = self._calculate_pattern_confidence(context_data, trigger_words)
        
        pattern = ContextPattern(
            trigger_text=trigger_words,
            bem_block=block,
            bem_element=element or '',
            confidence=confidence,
            examples=[bem_name],
            spatial_indicators=list(set(spatial_indicators))
        )
        
        return pattern
    
    def _parse_bem_name(self, bem_name: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """Parse BEM name into components."""
        try:
            # Handle modifiers (--) 
            parts = bem_name.split('--')
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
    
    def _find_common_triggers(self, text_list: List[str]) -> List[str]:
        """Find common words that trigger this pattern."""
        if not text_list:
            return []
        
        # Clean and tokenize all text
        all_words = []
        for text in text_list:
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            words = [w for w in clean_text.split() if len(w) > 2]
            all_words.extend(words)
        
        # Count word frequency
        word_counts = Counter(all_words)
        
        # Filter meaningful words
        stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'you', 'your', 'are', 'can', 'will', 'have', 'has'}
        
        triggers = []
        for word, count in word_counts.most_common(10):
            if (count >= max(2, len(text_list) * 0.3) and  # Appears in at least 30% of examples
                word not in stop_words and 
                len(word) > 2):
                triggers.append(word)
        
        return triggers[:5]  # Top 5 triggers
    
    def _calculate_pattern_confidence(self, context_data: List[Dict], triggers: List[str]) -> float:
        """Calculate confidence score for pattern."""
        if not context_data or not triggers:
            return 0.0
        
        # Check how consistently triggers appear
        trigger_matches = 0
        total_contexts = len(context_data)
        
        for ctx_info in context_data:
            context = ctx_info['context']
            context_text = f"{context.label_text or ''} {' '.join(context.nearby_text or [])}".lower()
            
            if any(trigger in context_text for trigger in triggers):
                trigger_matches += 1
        
        # Base confidence on trigger consistency
        trigger_confidence = trigger_matches / total_contexts if total_contexts > 0 else 0
        
        # Boost confidence if we have many examples
        example_boost = min(total_contexts / 10, 0.3)  # Up to 30% boost for 10+ examples
        
        return min(trigger_confidence + example_boost, 1.0)
    
    def analyze_spatial_patterns(self, examples: List[TrainingExample]) -> List[SpatialPattern]:
        """Analyze spatial positioning patterns."""
        logger.info("Analyzing spatial patterns")
        
        # Group fields by spatial regions
        spatial_regions = defaultdict(list)
        
        for example in examples:
            for pdf_field in example.pdf_fields:
                field_id = pdf_field.field_id
                
                if field_id in example.field_correlations:
                    bem_name = example.field_correlations[field_id]
                    bem_parts = self._parse_bem_name(bem_name)
                    
                    if bem_parts:
                        block, element, _ = bem_parts
                        
                        x = pdf_field.coordinates.get('x', 0)
                        y = pdf_field.coordinates.get('y', 0)
                        
                        # Create spatial region key
                        region_x = int(x // 100) * 100  # 100-point grid
                        region_y = int(y // 100) * 100
                        region_key = f"{region_x},{region_y}"
                        
                        spatial_regions[region_key].append({
                            'field': pdf_field,
                            'bem_name': bem_name,
                            'block': block,
                            'element': element or '',
                            'x': x,
                            'y': y
                        })
        
        # Analyze each spatial region
        patterns = []
        
        for region_key, fields in spatial_regions.items():
            if len(fields) < 3:  # Need multiple fields for pattern
                continue
            
            pattern = self._analyze_spatial_region(region_key, fields)
            if pattern and pattern.confidence >= 0.4:
                patterns.append(pattern)
        
        logger.info(f"Found {len(patterns)} spatial patterns")
        return patterns
    
    def _analyze_spatial_region(self, region_key: str, fields: List[Dict]) -> Optional[SpatialPattern]:
        """Analyze fields in a spatial region."""
        if len(fields) < 3:
            return None
        
        # Find most common block in this region
        blocks = [f['block'] for f in fields]
        block_counts = Counter(blocks)
        most_common_block = block_counts.most_common(1)[0][0]
        
        # Calculate position ranges
        x_coords = [f['x'] for f in fields]
        y_coords = [f['y'] for f in fields]
        
        position_range = {
            'x': (min(x_coords), max(x_coords)),
            'y': (min(y_coords), max(y_coords)),
            'width': (0, max([f['field'].coordinates.get('width', 0) for f in fields])),
            'height': (0, max([f['field'].coordinates.get('height', 0) for f in fields]))
        }
        
        # Determine field sequence (left-to-right, top-to-bottom)
        sorted_fields = sorted(fields, key=lambda f: (f['y'], f['x']))
        field_sequence = [f['element'] for f in sorted_fields if f['element']]
        
        # Calculate confidence based on block consistency
        block_consistency = block_counts[most_common_block] / len(fields)
        
        # Boost confidence if there's a clear sequence
        sequence_boost = 0.2 if len(set(field_sequence)) == len(field_sequence) else 0
        
        confidence = min(block_consistency + sequence_boost, 1.0)
        
        pattern = SpatialPattern(
            position_range=position_range,
            typical_block=most_common_block,
            field_sequence=field_sequence,
            confidence=confidence,
            examples=[f['bem_name'] for f in fields[:5]]  # Sample examples
        )
        
        return pattern
    
    def build_pattern_database(self, examples: List[TrainingExample]) -> PatternDatabase:
        """Create searchable database of naming patterns."""
        logger.info("Building pattern database")
        
        database = PatternDatabase()
        
        # Collect all BEM names and their contexts
        all_bem_names = []
        for example in examples:
            all_bem_names.extend(example.field_correlations.values())
        
        # Extract naming patterns (block, element, modifier frequencies)
        from .csv_schema import CSVSchemaParser
        
        # Create temporary CSV mappings for pattern extraction
        temp_mappings = []
        for example in examples:
            for field_id, bem_name in example.field_correlations.items():
                # Find the corresponding field
                pdf_field = next((f for f in example.pdf_fields if f.field_id == field_id), None)
                if pdf_field:
                    temp_mapping = CSVFieldMapping(
                        id=0,
                        label=pdf_field.field_name or '',
                        description='',
                        api_name=bem_name,
                        field_type=pdf_field.field_type or '',
                        page=1,
                        x=pdf_field.coordinates.get('x', 0),
                        y=pdf_field.coordinates.get('y', 0),
                        width=pdf_field.coordinates.get('width', 0),
                        height=pdf_field.coordinates.get('height', 0)
                    )
                    temp_mappings.append(temp_mapping)
        
        # Extract naming patterns
        parser = CSVSchemaParser()
        naming_patterns = parser.extract_naming_patterns(temp_mappings)
        database.naming_patterns = naming_patterns
        
        # Build keyword index for fast lookup
        database.pattern_index = self._build_pattern_index(database)
        
        logger.info(f"Built pattern database with {len(naming_patterns)} naming patterns")
        return database
    
    def _build_pattern_index(self, database: PatternDatabase) -> Dict[str, List[int]]:
        """Build keyword index for pattern lookup."""
        index = defaultdict(list)
        
        # Index context patterns
        for i, pattern in enumerate(database.context_patterns):
            for trigger in pattern.trigger_text:
                index[trigger.lower()].append(('context', i))
        
        # Index naming patterns
        for i, pattern in enumerate(database.naming_patterns):
            for trigger in pattern.context_triggers:
                index[trigger.lower()].append(('naming', i))
            
            # Also index the pattern value itself
            index[pattern.pattern_value.lower()].append(('naming', i))
        
        return dict(index)
    
    def generate_pattern_report(self, database: PatternDatabase) -> AnalysisReport:
        """Generate comprehensive analysis report."""
        logger.info("Generating pattern analysis report")
        
        total_examples = len(self.analyzed_examples)
        total_fields = sum(len(ex.pdf_fields) for ex in self.analyzed_examples)
        
        # Pattern coverage statistics
        pattern_coverage = {
            'context_patterns': len(database.context_patterns),
            'spatial_patterns': len(database.spatial_patterns),
            'naming_patterns': len(database.naming_patterns)
        }
        
        # Confidence distribution
        all_confidences = []
        all_confidences.extend([p.confidence for p in database.context_patterns])
        all_confidences.extend([p.confidence for p in database.spatial_patterns])
        all_confidences.extend([p.confidence for p in database.naming_patterns])
        
        confidence_distribution = {
            'high (>0.8)': sum(1 for c in all_confidences if c > 0.8),
            'medium (0.5-0.8)': sum(1 for c in all_confidences if 0.5 <= c <= 0.8),
            'low (<0.5)': sum(1 for c in all_confidences if c < 0.5)
        }
        
        # Common patterns
        block_patterns = [p for p in database.naming_patterns if p.pattern_type == 'block']
        element_patterns = [p for p in database.naming_patterns if p.pattern_type == 'element']
        
        common_blocks = [p.pattern_value for p in sorted(block_patterns, key=lambda x: x.frequency, reverse=True)][:10]
        common_elements = [p.pattern_value for p in sorted(element_patterns, key=lambda x: x.frequency, reverse=True)][:10]
        
        # Spatial clusters
        spatial_clusters = []
        for pattern in database.spatial_patterns:
            cluster_info = {
                'block': pattern.typical_block,
                'region': f"({pattern.position_range['x'][0]:.0f}, {pattern.position_range['y'][0]:.0f})",
                'field_count': len(pattern.field_sequence),
                'confidence': pattern.confidence
            }
            spatial_clusters.append(cluster_info)
        
        # Generate recommendations
        recommendations = []
        
        if len(database.context_patterns) < 10:
            recommendations.append("Consider adding more training data to improve context pattern detection")
        
        if confidence_distribution['low (<0.5)'] > confidence_distribution['high (>0.8)']:
            recommendations.append("Many patterns have low confidence - review training data quality")
        
        if len(common_blocks) < 5:
            recommendations.append("Limited block diversity - consider standardizing block naming conventions")
        
        report = AnalysisReport(
            total_examples=total_examples,
            total_fields=total_fields,
            pattern_coverage=pattern_coverage,
            confidence_distribution=confidence_distribution,
            common_blocks=common_blocks,
            common_elements=common_elements,
            spatial_clusters=spatial_clusters,
            recommendations=recommendations
        )
        
        logger.info("Pattern analysis report generated")
        return report