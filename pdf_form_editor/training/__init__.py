"""Training data integration and pattern analysis module.

This module provides functionality for loading training data from CSV/PDF pairs,
analyzing successful BEM naming patterns, and building a searchable pattern database
for intelligent field name generation.
"""

from .data_loader import TrainingDataLoader, TrainingPair, TrainingExample
from .csv_schema import CSVSchemaParser, CSVFieldMapping
from .pattern_analyzer import PatternAnalyzer, ContextPattern, SpatialPattern
from .similarity_matcher import SimilarityMatcher, SimilarMatch, BEMCandidate

__all__ = [
    'TrainingDataLoader',
    'TrainingPair', 
    'TrainingExample',
    'CSVSchemaParser',
    'CSVFieldMapping',
    'PatternAnalyzer',
    'ContextPattern',
    'SpatialPattern', 
    'SimilarityMatcher',
    'SimilarMatch',
    'BEMCandidate'
]