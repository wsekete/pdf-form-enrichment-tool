"""Training data discovery and loading system."""

import os
import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from ..core.field_extractor import FormField, FieldContext
from ..core.constants import TrainingConstants, ErrorConstants
from .csv_schema import CSVFieldMapping
import logging
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class TrainingPair:
    """Represents a matched PDF/CSV training pair."""
    pdf_path: str
    csv_path: str
    pair_id: str
    validation_status: str = 'unknown'
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class TrainingExample:
    """Complete training example with PDF fields and CSV mappings."""
    pdf_fields: List[FormField]  # From Phase 1 extraction
    csv_mappings: List[CSVFieldMapping]  # Target BEM names
    field_correlations: Dict[str, str]  # PDF field ID -> CSV row mapping
    context_data: List[FieldContext]  # From Phase 1 context extraction
    confidence: float = 0.0  # Quality score for this training example
    
    def __post_init__(self):
        if not self.field_correlations:
            self.field_correlations = {}
        if not self.context_data:
            self.context_data = []


@dataclass
class ValidationReport:
    """Training data validation results."""
    total_pairs: int
    valid_pairs: int
    invalid_pairs: int
    issues: List[str]
    pair_details: Dict[str, List[str]]  # pair_id -> issues
    
    def __post_init__(self):
        if not self.issues:
            self.issues = []
        if not self.pair_details:
            self.pair_details = {}
    
    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_pairs == 0:
            return 0.0
        return self.valid_pairs / self.total_pairs


class TrainingDataLoader:
    """Load and validate training data from CSV/PDF pairs."""
    
    def __init__(self, data_directory: str = "./samples", pdf_analyzer=None, field_extractor=None, context_extractor=None):
        """Initialize with path to CSV/PDF training pairs and optional dependencies."""
        self.data_directory = Path(data_directory)
        self.pdf_pattern = re.compile(r'(.+)_parsed\.pdf$')
        self.csv_pattern = re.compile(r'(.+)_parsed_correct_mapping\.csv$')
        
        # Optional dependency injection to avoid circular imports
        self._pdf_analyzer_class = pdf_analyzer
        self._field_extractor_class = field_extractor  
        self._context_extractor_class = context_extractor
        
        if not self.data_directory.exists():
            raise FileNotFoundError(f"Training data directory not found: {data_directory}")
    
    def discover_training_pairs(self) -> List[TrainingPair]:
        """Scan directory for matching CSV/PDF pairs."""
        logger.info(f"Discovering training pairs in {self.data_directory}")
        
        # Find all PDF and CSV files
        pdf_files = {}
        csv_files = {}
        
        for file_path in self.data_directory.glob("*"):
            if file_path.is_file():
                if file_path.suffix.lower() == '.pdf':
                    match = self.pdf_pattern.match(file_path.name)
                    if match:
                        base_name = match.group(1)
                        pdf_files[base_name] = str(file_path)
                
                elif file_path.suffix.lower() == '.csv':
                    match = self.csv_pattern.match(file_path.name)
                    if match:
                        base_name = match.group(1)
                        csv_files[base_name] = str(file_path)
        
        # Match PDF and CSV pairs
        pairs = []
        for base_name in pdf_files:
            if base_name in csv_files:
                pair = TrainingPair(
                    pdf_path=pdf_files[base_name],
                    csv_path=csv_files[base_name],
                    pair_id=base_name,
                    validation_status='discovered'
                )
                pairs.append(pair)
                logger.info(f"Found training pair: {base_name}")
            else:
                logger.warning(f"PDF without matching CSV: {base_name}")
        
        # Check for orphaned CSV files
        for base_name in csv_files:
            if base_name not in pdf_files:
                logger.warning(f"CSV without matching PDF: {base_name}")
        
        logger.info(f"Discovered {len(pairs)} training pairs")
        return pairs
    
    def load_formfield_examples(self, examples_path: str = "./samples/FormField_examples.csv") -> List[CSVFieldMapping]:
        """Load the comprehensive FormField examples for pattern learning."""
        logger.info(f"Loading FormField examples from {examples_path}")
        
        if not Path(examples_path).exists():
            logger.warning(f"FormField examples not found: {examples_path}")
            return []
        
        mappings = []
        with open(examples_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                try:
                    # Extract BEM name from apiName column
                    api_name = row.get('apiName', row.get('Api name', ''))
                    label = row.get('label', row.get('Label', ''))
                    field_type = row.get('type', row.get('Type', 'TextField'))
                    
                    # Skip empty or invalid entries
                    if not api_name or not label:
                        continue
                    
                    # Convert field type
                    type_mapping = {
                        'TextField': 'text',
                        'Checkbox': 'checkbox', 
                        'RadioButton': 'radio',
                        'RadioGroup': 'radio'
                    }
                    normalized_type = type_mapping.get(field_type, 'text')
                    
                    mapping = CSVFieldMapping(
                        id=i,
                        label=label,
                        description=row.get('description', ''),
                        api_name=api_name,
                        field_type=normalized_type,
                        page=int(row.get('page', row.get('Page', 0))),
                        x=float(row.get('x', row.get('X', 0))),
                        y=float(row.get('y', row.get('Y', 0))),
                        width=float(row.get('width', row.get('Width', 0))),
                        height=float(row.get('height', row.get('Height', 0))),
                        section_id=int(row['sectionId']) if row.get('sectionId') else None,
                        parent_id=int(row['parentId']) if row.get('parentId') else None
                    )
                    mappings.append(mapping)
                    
                except ValueError as e:
                    logger.debug(f"Skipping FormField example row {i} - invalid data format: {str(e)}")
                    continue
                except KeyError as e:
                    logger.debug(f"Skipping FormField example row {i} - missing required field {str(e)}")
                    continue
        
        logger.info(f"Loaded {len(mappings)} FormField examples")
        return mappings

    def load_training_pair(self, pdf_path: str, csv_path: str) -> TrainingExample:
        """Load and validate a single training pair."""
        logger.info(f"Loading training pair: {Path(pdf_path).name}")
        
        try:
            # Load PDF fields using Phase 1 extraction with dependency injection
            if self._pdf_analyzer_class:
                PDFAnalyzer = self._pdf_analyzer_class
            else:
                from ..core.pdf_analyzer import PDFAnalyzer
                
            if self._field_extractor_class:
                FieldExtractor = self._field_extractor_class
            else:
                from ..core.field_extractor import FieldExtractor
                
            if self._context_extractor_class:
                ContextExtractor = self._context_extractor_class
            else:
                from ..core.field_extractor import ContextExtractor
            
            # Initialize with PDF file
            analyzer = PDFAnalyzer(pdf_path)
            extractor = FieldExtractor(analyzer)
            context_extractor = ContextExtractor(analyzer)
            
            # Extract form fields
            pdf_fields = extractor.extract_form_fields()
            
            # Extract field contexts
            contexts = context_extractor.extract_all_contexts(pdf_fields)
            context_list = list(contexts.values())  # Convert dict to list
            
            # Load CSV mappings
            csv_mappings = self._load_csv_mappings(csv_path)
            
            # Correlate PDF fields with CSV mappings
            correlations = self._correlate_fields(pdf_fields, csv_mappings)
            
            # Calculate confidence based on correlation quality
            confidence = self._calculate_confidence(pdf_fields, csv_mappings, correlations)
            
            example = TrainingExample(
                pdf_fields=pdf_fields,
                csv_mappings=csv_mappings,
                field_correlations=correlations,
                context_data=context_list,
                confidence=confidence
            )
            
            logger.info(f"Loaded training example with {len(pdf_fields)} PDF fields, "
                       f"{len(csv_mappings)} CSV mappings, confidence: {confidence:.2f}")
            
            return example
            
        except FileNotFoundError as e:
            logger.error(f"Training pair file not found - {pdf_path}: {str(e)}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied accessing training pair - {pdf_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to load training pair {pdf_path}: {str(e)}")
            # Could add fallback behavior here if needed
            raise
    
    def _load_csv_mappings(self, csv_path: str) -> List[CSVFieldMapping]:
        """Load CSV field mappings."""
        import csv
        
        mappings = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                try:
                    mapping = CSVFieldMapping(
                        id=int(row.get('ID', i)),
                        label=row.get('Label', ''),
                        description=row.get('Description', ''),
                        api_name=row.get('Api name', ''),  # This is the correct BEM name
                        field_type=row.get('Type', 'TextField'),
                        page=int(row.get('Page', 1)),
                        x=float(row.get('X', 0)),
                        y=float(row.get('Y', 0)),
                        width=float(row.get('Width', 0)),
                        height=float(row.get('Height', 0)),
                        section_id=int(row['Section ID']) if row.get('Section ID') else None,
                        parent_id=int(row['Parent ID']) if row.get('Parent ID') else None,
                        additional_properties={k: v for k, v in row.items() 
                                            if k not in ['ID', 'Label', 'Description', 'Api name', 
                                                       'Type', 'Page', 'X', 'Y', 'Width', 'Height',
                                                       'Section ID', 'Parent ID']}
                    )
                    mappings.append(mapping)
                    
                except ValueError as e:
                    logger.warning(f"Skipping CSV row {i} in {csv_path} - invalid data format: {str(e)}")
                    continue
                except KeyError as e:
                    logger.warning(f"Skipping CSV row {i} in {csv_path} - missing required field {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing CSV row {i} in {csv_path}: {str(e)}")
                    continue
        
        logger.info(f"Loaded {len(mappings)} CSV field mappings from {csv_path}")
        return mappings
    
    def _correlate_fields(self, pdf_fields: List[FormField], 
                         csv_mappings: List[CSVFieldMapping]) -> Dict[str, str]:
        """Correlate PDF fields with CSV mappings using spatial proximity."""
        correlations = {}
        
        for pdf_field in pdf_fields:
            best_match = None
            best_distance = float('inf')
            
            # Convert PDF field coordinates (rect is [x1, y1, x2, y2])
            pdf_x = pdf_field.rect[0] if len(pdf_field.rect) >= 1 else 0
            pdf_y = pdf_field.rect[1] if len(pdf_field.rect) >= 2 else 0
            
            for csv_mapping in csv_mappings:
                # Calculate spatial distance
                distance = ((pdf_x - csv_mapping.x) ** 2 + 
                           (pdf_y - csv_mapping.y) ** 2) ** 0.5
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = csv_mapping
            
            # Accept match if distance is reasonable (within threshold)
            if best_match and best_distance < TrainingConstants.SPATIAL_CORRELATION_THRESHOLD:
                correlations[pdf_field.id] = best_match.api_name
            else:
                logger.warning(f"No close CSV match for PDF field {pdf_field.id} "
                             f"at ({pdf_x}, {pdf_y})")
        
        logger.info(f"Correlated {len(correlations)} PDF fields with CSV mappings")
        return correlations
    
    def _calculate_confidence(self, pdf_fields: List[FormField], 
                            csv_mappings: List[CSVFieldMapping],
                            correlations: Dict[str, str]) -> float:
        """Calculate confidence score for training example."""
        if not pdf_fields or not csv_mappings:
            return 0.0
        
        # Base confidence on correlation ratio
        correlation_ratio = len(correlations) / len(pdf_fields)
        
        # Bonus for field count similarity
        count_similarity = min(len(pdf_fields), len(csv_mappings)) / max(len(pdf_fields), len(csv_mappings))
        
        # Combine factors
        confidence = (correlation_ratio * TrainingConstants.CORRELATION_RATIO_WEIGHT) + (count_similarity * TrainingConstants.COUNT_SIMILARITY_WEIGHT)
        
        return min(confidence, 1.0)
    
    def validate_training_data(self, pairs: List[TrainingPair]) -> ValidationReport:
        """Comprehensive validation of training data quality."""
        logger.info(f"Validating {len(pairs)} training pairs")
        
        valid_pairs = 0
        issues = []
        pair_details = {}
        
        for pair in pairs:
            pair_issues = []
            
            # Check file existence
            if not Path(pair.pdf_path).exists():
                pair_issues.append(f"PDF file not found: {pair.pdf_path}")
            
            if not Path(pair.csv_path).exists():
                pair_issues.append(f"CSV file not found: {pair.csv_path}")
            
            # Try to load the pair
            if not pair_issues:
                try:
                    example = self.load_training_pair(pair.pdf_path, pair.csv_path)
                    
                    # Validate BEM naming in CSV
                    bem_issues = self._validate_bem_names(example.csv_mappings)
                    pair_issues.extend(bem_issues)
                    
                    # Check correlation quality
                    if example.confidence < ErrorConstants.MIN_CONFIDENCE_THRESHOLD:
                        pair_issues.append(f"Low field correlation confidence: {example.confidence:.2f}")
                    
                    if not pair_issues:
                        valid_pairs += 1
                        pair.validation_status = 'valid'
                    else:
                        pair.validation_status = 'issues'
                        
                except Exception as e:
                    pair_issues.append(f"Failed to load pair: {str(e)}")
                    pair.validation_status = 'invalid'
            else:
                pair.validation_status = 'invalid'
            
            if pair_issues:
                pair_details[pair.pair_id] = pair_issues
                issues.extend([f"{pair.pair_id}: {issue}" for issue in pair_issues])
                pair.issues = pair_issues
        
        report = ValidationReport(
            total_pairs=len(pairs),
            valid_pairs=valid_pairs,
            invalid_pairs=len(pairs) - valid_pairs,
            issues=issues,
            pair_details=pair_details
        )
        
        logger.info(f"Validation complete: {valid_pairs}/{len(pairs)} pairs valid")
        return report
    
    def _validate_bem_names(self, mappings: List[CSVFieldMapping]) -> List[str]:
        """Validate BEM naming conventions in CSV data."""
        issues = []
        bem_pattern = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*(_[a-z][a-z0-9]*(-[a-z0-9]+)*)?(--[a-z][a-z0-9]*(-[a-z0-9]+)*)?$')
        
        seen_names = set()
        
        for mapping in mappings:
            api_name = mapping.api_name
            
            if not api_name:
                issues.append(f"Empty API name for field {mapping.id}")
                continue
            
            # Check BEM syntax
            if not bem_pattern.match(api_name):
                issues.append(f"Invalid BEM syntax: {api_name}")
            
            # Check uniqueness
            if api_name in seen_names:
                issues.append(f"Duplicate API name: {api_name}")
            else:
                seen_names.add(api_name)
            
            # Check length
            if len(api_name) > TrainingConstants.MAX_BEM_NAME_LENGTH:
                issues.append(f"API name too long: {api_name}")
        
        return issues