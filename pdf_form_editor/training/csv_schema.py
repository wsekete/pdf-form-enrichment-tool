"""CSV schema parser and validator for training data."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import Counter

import logging
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class CSVFieldMapping:
    """Field mapping from CSV training data."""
    id: int
    label: str
    description: str
    api_name: str  # Target BEM name
    field_type: str
    page: int
    x: float
    y: float
    width: float
    height: float
    section_id: Optional[int] = None
    parent_id: Optional[int] = None
    additional_properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_properties is None:
            self.additional_properties = {}


@dataclass
class ValidationResult:
    """Validation result for BEM names or schema."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class NamingPattern:
    """Reusable naming pattern extracted from training data."""
    pattern_type: str  # 'block', 'element', 'modifier'
    pattern_value: str  # The actual pattern (e.g., 'owner', 'contact')
    context_triggers: List[str]  # Text that suggests this pattern
    frequency: int  # How often this pattern appears
    confidence: float  # Reliability score
    examples: List[str]  # Sample BEM names using this pattern
    
    def __post_init__(self):
        if self.context_triggers is None:
            self.context_triggers = []
        if self.examples is None:
            self.examples = []


class CSVSchemaParser:
    """Parse CSV files matching the database schema format."""
    
    REQUIRED_COLUMNS = [
        'ID', 'Label', 'Description', 'Api name', 'Type', 'Page', 
        'X', 'Y', 'Width', 'Height', 'Section ID', 'Parent ID'
    ]
    
    # BEM pattern for validation
    BEM_PATTERN = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*(_[a-z][a-z0-9]*(-[a-z0-9]+)*)?(--[a-z][a-z0-9]*(-[a-z0-9]+)*)?$')
    
    def __init__(self):
        self.parsed_files = []
        self.naming_patterns = []
    
    def parse_csv_file(self, csv_path: str) -> List[CSVFieldMapping]:
        """Parse CSV and extract field mappings."""
        logger.info(f"Parsing CSV file: {Path(csv_path).name}")
        
        mappings = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
                reader = csv.DictReader(f)
                
                # Validate required columns
                missing_columns = set(self.REQUIRED_COLUMNS) - set(reader.fieldnames or [])
                if missing_columns:
                    logger.warning(f"Missing required columns in {csv_path}: {missing_columns}")
                
                for i, row in enumerate(reader, 1):
                    try:
                        mapping = self._parse_csv_row(row, i)
                        if mapping:
                            mappings.append(mapping)
                    except Exception as e:
                        logger.warning(f"Skipping invalid row {i} in {csv_path}: {str(e)}")
                        continue
            
            logger.info(f"Parsed {len(mappings)} field mappings from {csv_path}")
            self.parsed_files.append(csv_path)
            
        except Exception as e:
            logger.error(f"Failed to parse CSV file {csv_path}: {str(e)}")
            raise
        
        return mappings
    
    def _parse_csv_row(self, row: Dict[str, str], row_num: int) -> Optional[CSVFieldMapping]:
        """Parse a single CSV row into a CSVFieldMapping."""
        try:
            # Handle missing or empty values
            def get_value(key: str, default: Any = '', convert_func=None):
                value = row.get(key, default)
                if value == '' or value is None:
                    return default
                if convert_func:
                    return convert_func(value)
                return value
            
            # Try different column name formats (original vs FormField_examples.csv format)
            mapping = CSVFieldMapping(
                id=get_value('ID', get_value('id', 0), int),
                label=get_value('Label', get_value('label', '')),
                description=get_value('Description', get_value('description', '')),
                api_name=get_value('Api name', get_value('apiName', '')),
                field_type=get_value('Type', get_value('type', '')),
                page=get_value('Page', get_value('page', 1), int),
                x=get_value('X', get_value('x', 0.0), float),
                y=get_value('Y', get_value('y', 0.0), float),
                width=get_value('Width', get_value('width', 0.0), float),
                height=get_value('Height', get_value('height', 0.0), float),
                section_id=get_value('Section ID', get_value('sectionId', None), lambda x: int(x) if x else None),
                parent_id=get_value('Parent ID', get_value('parentId', None), lambda x: int(x) if x else None),
                additional_properties={
                    k: v for k, v in row.items() 
                    if k not in self.REQUIRED_COLUMNS and k not in ['id', 'label', 'description', 'apiName', 'type', 'page', 'x', 'y', 'width', 'height', 'sectionId', 'parentId'] and v
                }
            )
            
            return mapping
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid data in row {row_num}: {str(e)}")
            return None
    
    def validate_bem_names(self, mappings: List[CSVFieldMapping]) -> ValidationResult:
        """Validate BEM naming conventions in CSV."""
        logger.info(f"Validating BEM names for {len(mappings)} mappings")
        
        errors = []
        warnings = []
        suggestions = []
        seen_names = set()
        
        for mapping in mappings:
            api_name = mapping.api_name
            
            if not api_name:
                errors.append(f"Empty API name for field {mapping.id} (Label: {mapping.label})")
                continue
            
            # Check BEM syntax
            if not self.BEM_PATTERN.match(api_name):
                errors.append(f"Invalid BEM syntax: '{api_name}' for field {mapping.id}")
                suggestions.append(f"Consider renaming '{api_name}' to follow block_element pattern")
            
            # Check uniqueness
            if api_name in seen_names:
                errors.append(f"Duplicate API name: '{api_name}'")
            else:
                seen_names.add(api_name)
            
            # Check length
            if len(api_name) > 50:
                warnings.append(f"API name '{api_name}' is long ({len(api_name)} chars)")
            
            # Check for proper separator usage
            if '_' not in api_name:
                warnings.append(f"API name '{api_name}' lacks block_element structure")
        
        is_valid = len(errors) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
        
        logger.info(f"BEM validation: {len(errors)} errors, {len(warnings)} warnings")
        return result
    
    def extract_naming_patterns(self, mappings: List[CSVFieldMapping]) -> List[NamingPattern]:
        """Extract reusable naming patterns from successful BEM names."""
        logger.info(f"Extracting naming patterns from {len(mappings)} mappings")
        
        block_patterns = Counter()
        element_patterns = Counter()
        modifier_patterns = Counter()
        
        # Context associations
        block_contexts = {}
        element_contexts = {}
        
        for mapping in mappings:
            api_name = mapping.api_name
            if not api_name or not self.BEM_PATTERN.match(api_name):
                continue
            
            # Parse BEM structure
            parts = self._parse_bem_structure(api_name)
            if not parts:
                continue
            
            block, element, modifier = parts
            
            # Count patterns
            block_patterns[block] += 1
            if element:
                element_patterns[element] += 1
            if modifier:
                modifier_patterns[modifier] += 1
            
            # Associate with context
            context_text = f"{mapping.label} {mapping.description}".lower()
            
            if block not in block_contexts:
                block_contexts[block] = []
            block_contexts[block].append(context_text)
            
            if element and element not in element_contexts:
                element_contexts[element] = []
            if element:
                element_contexts[element].append(context_text)
        
        patterns = []
        
        # Create block patterns
        for block, frequency in block_patterns.most_common():
            confidence = min(frequency / len(mappings), 1.0)
            triggers = self._extract_context_triggers(block_contexts.get(block, []))
            
            pattern = NamingPattern(
                pattern_type='block',
                pattern_value=block,
                context_triggers=triggers,
                frequency=frequency,
                confidence=confidence,
                examples=[m.api_name for m in mappings if m.api_name.startswith(block + '_')][:5]
            )
            patterns.append(pattern)
        
        # Create element patterns
        for element, frequency in element_patterns.most_common():
            confidence = min(frequency / len(mappings), 1.0)
            triggers = self._extract_context_triggers(element_contexts.get(element, []))
            
            pattern = NamingPattern(
                pattern_type='element',
                pattern_value=element,
                context_triggers=triggers,
                frequency=frequency,
                confidence=confidence,
                examples=[m.api_name for m in mappings if element in m.api_name][:5]
            )
            patterns.append(pattern)
        
        # Create modifier patterns  
        for modifier, frequency in modifier_patterns.most_common():
            confidence = min(frequency / len(mappings), 1.0)
            
            pattern = NamingPattern(
                pattern_type='modifier',
                pattern_value=modifier,
                context_triggers=[],
                frequency=frequency,
                confidence=confidence,
                examples=[m.api_name for m in mappings if modifier in m.api_name][:5]
            )
            patterns.append(pattern)
        
        logger.info(f"Extracted {len(patterns)} naming patterns")
        self.naming_patterns.extend(patterns)
        
        return patterns
    
    def _parse_bem_structure(self, api_name: str) -> Optional[tuple]:
        """Parse BEM structure into block, element, modifier."""
        try:
            # Split on modifiers first (--) 
            parts = api_name.split('--')
            base_name = parts[0]
            modifier = parts[1] if len(parts) > 1 else None
            
            # Split base on element separator (_)
            base_parts = base_name.split('_')
            if len(base_parts) >= 2:
                block = '_'.join(base_parts[:-1])  # Everything except last part
                element = base_parts[-1]  # Last part
            else:
                block = base_parts[0]
                element = None
            
            return (block, element, modifier)
            
        except Exception:
            return None
    
    def _extract_context_triggers(self, context_texts: List[str]) -> List[str]:
        """Extract common words/phrases that suggest this pattern."""
        if not context_texts:
            return []
        
        # Simple word frequency analysis
        words = []
        for text in context_texts:
            # Clean and split text
            clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
            words.extend(clean_text.split())
        
        # Count word frequency
        word_counts = Counter(words)
        
        # Filter out common stop words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        triggers = [
            word for word, count in word_counts.most_common(10)
            if len(word) > 2 and word not in stop_words and count > 1
        ]
        
        return triggers[:5]  # Top 5 triggers
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of extracted patterns."""
        if not self.naming_patterns:
            return {}
        
        block_patterns = [p for p in self.naming_patterns if p.pattern_type == 'block']
        element_patterns = [p for p in self.naming_patterns if p.pattern_type == 'element']
        modifier_patterns = [p for p in self.naming_patterns if p.pattern_type == 'modifier']
        
        return {
            'total_patterns': len(self.naming_patterns),
            'block_patterns': len(block_patterns),
            'element_patterns': len(element_patterns),
            'modifier_patterns': len(modifier_patterns),
            'top_blocks': [p.pattern_value for p in sorted(block_patterns, key=lambda x: x.frequency, reverse=True)][:5],
            'top_elements': [p.pattern_value for p in sorted(element_patterns, key=lambda x: x.frequency, reverse=True)][:5],
            'files_processed': len(self.parsed_files)
        }