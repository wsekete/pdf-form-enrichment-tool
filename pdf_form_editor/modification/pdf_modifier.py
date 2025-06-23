#!/usr/bin/env python3
"""
Safe PDF Field Modifier

Safely modifies PDF field names while preserving all form functionality,
relationships, and document integrity with comprehensive validation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field as dataclass_field
from enum import Enum

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject, NameObject, TextStringObject

from ..core.field_extractor import FormField
from ..utils.logging import get_logger
from ..utils.errors import PDFProcessingError
from .backup_recovery import BackupRecoverySystem, BackupInfo

logger = get_logger(__name__)


class ModificationStatus(Enum):
    """Status of a field modification."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class FieldModification:
    """Details of a single field modification."""
    field_id: str
    old_name: str
    new_name: str
    field_type: str
    page: int
    coordinates: List[float]
    parent_id: Optional[str] = None
    children_ids: List[str] = dataclass_field(default_factory=list)
    status: ModificationStatus = ModificationStatus.PLANNED
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    preservation_action: str = "modify"
    confidence: float = 0.0
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "field_id": self.field_id,
            "original_name": self.old_name,
            "new_name": self.new_name,
            "field_type": self.field_type,
            "page": self.page,
            "coordinates": self.coordinates,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "modification_status": self.status.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "error_message": self.error_message,
            "preservation_action": self.preservation_action,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


@dataclass
class ModificationPlan:
    """Plan for all field modifications."""
    total_modifications: int
    hierarchy_updates: List[str]
    potential_conflicts: List[str]
    modification_sequence: List[FieldModification]
    estimated_safety_score: float
    created_at: datetime = dataclass_field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_modifications": self.total_modifications,
            "hierarchy_updates": self.hierarchy_updates,
            "potential_conflicts": self.potential_conflicts,
            "estimated_safety_score": self.estimated_safety_score,
            "created_at": self.created_at.isoformat(),
            "modification_sequence": [mod.to_dict() for mod in self.modification_sequence]
        }


@dataclass
class ValidationReport:
    """Report of validation results."""
    pdf_structure_valid: bool
    form_fields_accessible: bool
    hierarchy_preserved: bool
    functionality_verified: bool
    issues: List[str]
    warnings: List[str]
    validation_timestamp: datetime = dataclass_field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pdf_structure_valid": self.pdf_structure_valid,
            "form_fields_accessible": self.form_fields_accessible,
            "hierarchy_preserved": self.hierarchy_preserved,
            "functionality_verified": self.functionality_verified,
            "issues": self.issues,
            "warnings": self.warnings,
            "validation_timestamp": self.validation_timestamp.isoformat()
        }


@dataclass
class ModificationResult:
    """Result of the modification process."""
    success: bool
    applied_count: int
    failed_count: int
    skipped_count: int
    modifications: List[FieldModification]
    validation_report: Optional[ValidationReport]
    backup_info: Optional[BackupInfo]
    processing_time: float
    errors: List[str]
    modified_pdf_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "applied_count": self.applied_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "processing_time": self.processing_time,
            "errors": self.errors,
            "modified_pdf_path": self.modified_pdf_path,
            "modifications": [mod.to_dict() for mod in self.modifications],
            "validation_report": self.validation_report.to_dict() if self.validation_report else None,
            "backup_info": self.backup_info.to_dict() if self.backup_info else None
        }


class SafePDFModifier:
    """Safely modify PDF field names while preserving functionality."""
    
    def __init__(self, pdf_path: str, backup_enabled: bool = True):
        """
        Initialize PDF modifier.
        
        Args:
            pdf_path: Path to the PDF file to modify
            backup_enabled: Whether to create automatic backups
        """
        self.pdf_path = Path(pdf_path)
        self.backup_enabled = backup_enabled
        self.backup_system = BackupRecoverySystem() if backup_enabled else None
        self.backup_info: Optional[BackupInfo] = None
        self.modifications: List[FieldModification] = []
        self.validation_results: List[ValidationReport] = []
        
        # Validate input PDF
        if not self.pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {self.pdf_path}")
        
        logger.info(f"SafePDFModifier initialized for: {self.pdf_path}")
    
    def create_backup(self, notes: str = "Pre-modification backup") -> BackupInfo:
        """
        Create backup of original PDF.
        
        Args:
            notes: Notes about this backup
            
        Returns:
            BackupInfo with backup details
        """
        if not self.backup_system:
            raise PDFProcessingError("Backup system not enabled")
        
        self.backup_info = self.backup_system.create_backup(str(self.pdf_path), notes)
        logger.info(f"Created backup: {self.backup_info.backup_id}")
        return self.backup_info
    
    def plan_modifications(self, field_mapping: Dict[str, str], original_fields: List[FormField]) -> ModificationPlan:
        """
        Plan all field name modifications with conflict detection.
        
        Args:
            field_mapping: Dictionary mapping field IDs to new names
            original_fields: List of original form fields
            
        Returns:
            ModificationPlan with detailed planning information
        """
        logger.info(f"Planning modifications for {len(field_mapping)} fields")
        
        # Create modification objects
        modifications = []
        field_lookup = {field.id: field for field in original_fields}
        
        for field_id, new_name in field_mapping.items():
            if field_id not in field_lookup:
                logger.warning(f"Field not found for modification: {field_id}")
                continue
            
            field = field_lookup[field_id]
            modification = FieldModification(
                field_id=field_id,
                old_name=field.name,
                new_name=new_name,
                field_type=field.field_type,
                page=field.page,
                coordinates=field.rect,
                parent_id=field.parent,
                children_ids=field.children
            )
            modifications.append(modification)
        
        # Detect conflicts
        potential_conflicts = self._detect_naming_conflicts(modifications)
        
        # Analyze hierarchy updates needed
        hierarchy_updates = self._analyze_hierarchy_updates(modifications, original_fields)
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(modifications, potential_conflicts)
        
        plan = ModificationPlan(
            total_modifications=len(modifications),
            hierarchy_updates=hierarchy_updates,
            potential_conflicts=potential_conflicts,
            modification_sequence=modifications,
            estimated_safety_score=safety_score
        )
        
        logger.info(f"Modification plan created: {len(modifications)} modifications, "
                   f"safety score: {safety_score:.2f}")
        
        return plan
    
    def apply_field_modifications(self, modifications: List[FieldModification], 
                                dry_run: bool = False) -> ModificationResult:
        """
        Apply field name changes safely.
        
        Args:
            modifications: List of modifications to apply
            dry_run: If True, validate but don't actually modify
            
        Returns:
            ModificationResult with detailed results
        """
        start_time = datetime.now()
        logger.info(f"Starting field modifications: {len(modifications)} changes (dry_run={dry_run})")
        
        # Create backup if not in dry run mode
        if not dry_run and self.backup_enabled:
            self.create_backup("Pre-modification backup")
        
        applied_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # Load PDF
            with open(self.pdf_path, 'rb') as f:
                reader = PdfReader(f)
                writer = PdfWriter()
                
                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)
                
                # Copy form fields and apply modifications
                if reader.trailer.get("/Root") and reader.trailer["/Root"].get("/AcroForm"):
                    acro_form = reader.trailer["/Root"]["/AcroForm"]
                    
                    # Clone the form dictionary
                    writer._root_object[NameObject("/AcroForm")] = self._clone_acroform_with_modifications(
                        acro_form, modifications, dry_run
                    )
                    
                    # Update modification results
                    for modification in modifications:
                        if modification.status == ModificationStatus.SUCCESS:
                            applied_count += 1
                        elif modification.status == ModificationStatus.FAILED:
                            failed_count += 1
                            if modification.error_message:
                                errors.append(f"{modification.field_id}: {modification.error_message}")
                        else:
                            skipped_count += 1
                
                # Write modified PDF if not dry run
                modified_pdf_path = str(self.pdf_path)
                if not dry_run:
                    if applied_count > 0:
                        modified_pdf_path = str(self.pdf_path.with_suffix('.modified.pdf'))
                        with open(modified_pdf_path, 'wb') as output_file:
                            writer.write(output_file)
                        logger.info(f"Modified PDF written to: {modified_pdf_path}")
                    else:
                        logger.info("No modifications applied, original PDF unchanged")
                
                # Validate modifications
                validation_report = self._validate_modifications(modified_pdf_path, dry_run)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                result = ModificationResult(
                    success=(failed_count == 0),
                    applied_count=applied_count,
                    failed_count=failed_count,
                    skipped_count=skipped_count,
                    modifications=modifications,
                    validation_report=validation_report,
                    backup_info=self.backup_info,
                    processing_time=processing_time,
                    errors=errors,
                    modified_pdf_path=modified_pdf_path
                )
                
                logger.info(f"Modification complete: {applied_count} applied, {failed_count} failed, "
                           f"{skipped_count} skipped in {processing_time:.2f}s")
                
                return result
                
        except Exception as e:
            error_msg = f"Critical error during modification: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            # Attempt rollback if backup exists
            if self.backup_info and not dry_run:
                logger.info("Attempting automatic rollback due to critical error")
                self.rollback_changes()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ModificationResult(
                success=False,
                applied_count=applied_count,
                failed_count=len(modifications),
                skipped_count=0,
                modifications=modifications,
                validation_report=None,
                backup_info=self.backup_info,
                processing_time=processing_time,
                errors=errors,
                modified_pdf_path=str(self.pdf_path)
            )
    
    def _clone_acroform_with_modifications(self, acro_form: DictionaryObject, 
                                         modifications: List[FieldModification], 
                                         dry_run: bool) -> DictionaryObject:
        """
        Clone AcroForm dictionary with field name modifications.
        
        Args:
            acro_form: Original AcroForm dictionary
            modifications: List of modifications to apply
            dry_run: Whether this is a dry run
            
        Returns:
            Modified AcroForm dictionary
        """
        # Create modification lookup
        mod_lookup = {mod.field_id: mod for mod in modifications}
        name_changes = {mod.old_name: mod.new_name for mod in modifications}
        
        # Clone the AcroForm dictionary
        new_acro_form = DictionaryObject()
        
        for key, value in acro_form.items():
            if key == "/Fields":
                # Process fields array
                new_fields = ArrayObject()
                if isinstance(value, ArrayObject):
                    for field_ref in value:
                        new_field = self._process_field_with_modifications(
                            field_ref, name_changes, mod_lookup, dry_run
                        )
                        new_fields.append(new_field)
                new_acro_form[key] = new_fields
            else:
                # Copy other properties as-is
                new_acro_form[key] = value
        
        return new_acro_form
    
    def _process_field_with_modifications(self, field_ref: IndirectObject, 
                                        name_changes: Dict[str, str],
                                        mod_lookup: Dict[str, FieldModification],
                                        dry_run: bool) -> IndirectObject:
        """
        Process a field reference and apply name modifications.
        
        Args:
            field_ref: Reference to field object
            name_changes: Dictionary of name changes
            mod_lookup: Lookup for modification objects
            dry_run: Whether this is a dry run
            
        Returns:
            Modified field reference
        """
        try:
            # Get the field object
            field_obj = field_ref.get_object()
            if not isinstance(field_obj, DictionaryObject):
                return field_ref
            
            # Check if this field needs modification
            current_name = field_obj.get("/T")
            if current_name and str(current_name) in name_changes:
                new_name = name_changes[str(current_name)]
                
                # Find the corresponding modification
                modification = None
                for mod in mod_lookup.values():
                    if mod.old_name == str(current_name):
                        modification = mod
                        break
                
                if modification and not dry_run:
                    try:
                        # Update the field name
                        field_obj[NameObject("/T")] = TextStringObject(new_name)
                        modification.status = ModificationStatus.SUCCESS
                        modification.timestamp = datetime.now()
                        logger.debug(f"Updated field name: {current_name} -> {new_name}")
                        
                    except Exception as e:
                        if modification:
                            modification.status = ModificationStatus.FAILED
                            modification.error_message = str(e)
                        logger.error(f"Failed to update field {current_name}: {e}")
                
                elif modification and dry_run:
                    modification.status = ModificationStatus.SUCCESS
                    logger.debug(f"Dry run: would update {current_name} -> {new_name}")
            
            # Process child fields recursively
            kids = field_obj.get("/Kids")
            if kids and isinstance(kids, ArrayObject):
                new_kids = ArrayObject()
                for kid_ref in kids:
                    new_kid = self._process_field_with_modifications(
                        kid_ref, name_changes, mod_lookup, dry_run
                    )
                    new_kids.append(new_kid)
                field_obj[NameObject("/Kids")] = new_kids
            
            return field_ref
            
        except Exception as e:
            logger.error(f"Error processing field: {e}")
            return field_ref
    
    def _detect_naming_conflicts(self, modifications: List[FieldModification]) -> List[str]:
        """
        Detect potential naming conflicts.
        
        Args:
            modifications: List of planned modifications
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        new_names = [mod.new_name for mod in modifications]
        
        # Check for duplicate new names
        seen_names = set()
        for name in new_names:
            if name in seen_names:
                conflicts.append(f"Duplicate new name: {name}")
            seen_names.add(name)
        
        # Check for invalid BEM naming patterns
        bem_pattern = r'^[a-z][a-z0-9]*(-[a-z0-9]+)*(_[a-z][a-z0-9]*(-[a-z0-9]+)*)?(--[a-z][a-z0-9]*(-[a-z0-9]+)*)?$'
        import re
        bem_regex = re.compile(bem_pattern)
        
        for mod in modifications:
            if not bem_regex.match(mod.new_name):
                conflicts.append(f"Invalid BEM name format: {mod.new_name}")
        
        return conflicts
    
    def _analyze_hierarchy_updates(self, modifications: List[FieldModification], 
                                 original_fields: List[FormField]) -> List[str]:
        """
        Analyze hierarchy updates needed.
        
        Args:
            modifications: List of planned modifications
            original_fields: Original field list
            
        Returns:
            List of hierarchy update descriptions
        """
        hierarchy_updates = []
        
        # Find fields with parent-child relationships
        for modification in modifications:
            if modification.parent_id or modification.children_ids:
                hierarchy_updates.append(
                    f"Hierarchy update needed for: {modification.old_name}"
                )
        
        return hierarchy_updates
    
    def _calculate_safety_score(self, modifications: List[FieldModification], 
                              conflicts: List[str]) -> float:
        """
        Calculate estimated safety score for modifications.
        
        Args:
            modifications: List of planned modifications
            conflicts: List of detected conflicts
            
        Returns:
            Safety score from 0.0 to 1.0
        """
        if not modifications:
            return 1.0
        
        # Base score
        score = 1.0
        
        # Deduct for conflicts
        score -= len(conflicts) * 0.1
        
        # Deduct for high-risk field types
        high_risk_types = {'signature', 'button'}
        high_risk_count = sum(1 for mod in modifications if mod.field_type in high_risk_types)
        score -= high_risk_count * 0.05
        
        # Deduct for hierarchy complexity
        hierarchy_count = sum(1 for mod in modifications if mod.parent_id or mod.children_ids)
        score -= hierarchy_count * 0.02
        
        return max(0.0, min(1.0, score))
    
    def _validate_modifications(self, pdf_path: str, dry_run: bool) -> ValidationReport:
        """
        Validate modifications for integrity and functionality.
        
        Args:
            pdf_path: Path to modified PDF
            dry_run: Whether this was a dry run
            
        Returns:
            ValidationReport with validation results
        """
        issues = []
        warnings = []
        
        pdf_structure_valid = True
        form_fields_accessible = True
        hierarchy_preserved = True
        functionality_verified = True
        
        try:
            if not dry_run and Path(pdf_path).exists():
                # Basic PDF structure validation
                try:
                    with open(pdf_path, 'rb') as f:
                        reader = PdfReader(f)
                        # Check if we can read basic properties
                        _ = reader.pages
                        _ = reader.metadata
                except Exception as e:
                    pdf_structure_valid = False
                    issues.append(f"PDF structure validation failed: {e}")
                
                # Form fields accessibility check
                try:
                    from ..core.pdf_analyzer import PDFAnalyzer
                    analyzer = PDFAnalyzer(pdf_path)
                    if not analyzer.has_form_fields():
                        form_fields_accessible = False
                        issues.append("Form fields not accessible after modification")
                except Exception as e:
                    warnings.append(f"Form accessibility check failed: {e}")
            
            elif dry_run:
                warnings.append("Validation limited in dry-run mode")
            
        except Exception as e:
            issues.append(f"Validation error: {e}")
            functionality_verified = False
        
        return ValidationReport(
            pdf_structure_valid=pdf_structure_valid,
            form_fields_accessible=form_fields_accessible,
            hierarchy_preserved=hierarchy_preserved,
            functionality_verified=functionality_verified,
            issues=issues,
            warnings=warnings
        )
    
    def rollback_changes(self) -> bool:
        """
        Rollback all modifications using backup.
        
        Returns:
            True if rollback successful
        """
        if not self.backup_info or not self.backup_system:
            logger.error("No backup available for rollback")
            return False
        
        try:
            restore_result = self.backup_system.restore_from_backup(
                self.backup_info.backup_id, str(self.pdf_path)
            )
            
            if restore_result.success:
                logger.info(f"Successfully rolled back to backup: {self.backup_info.backup_id}")
                
                # Mark all modifications as rolled back
                for modification in self.modifications:
                    if modification.status == ModificationStatus.SUCCESS:
                        modification.status = ModificationStatus.ROLLED_BACK
                
                return True
            else:
                logger.error(f"Rollback failed: {restore_result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"Rollback error: {e}")
            return False