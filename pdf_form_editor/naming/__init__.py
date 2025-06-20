"""
BEM Name Generation Module

This module provides intelligent BEM (Block Element Modifier) name generation
for PDF form fields using training patterns and context analysis.
"""

from .bem_generator import BEMNameGenerator, BEMResult, BEMCandidate
from .pattern_learner import PatternLearner, SpatialSuggestion, HierarchySuggestion  
from .rule_engine import RuleBasedEngine, SemanticAnalysis
from .name_validator import BEMNameValidator, ValidationResult, UniquenessResult

__all__ = [
    'BEMNameGenerator',
    'BEMResult', 
    'BEMCandidate',
    'PatternLearner',
    'SpatialSuggestion',
    'HierarchySuggestion',
    'RuleBasedEngine', 
    'SemanticAnalysis',
    'BEMNameValidator',
    'ValidationResult',
    'UniquenessResult'
]