#!/usr/bin/env python3
"""
PDF Integrity Validator

Comprehensive validation of PDF integrity after field modifications to ensure
form functionality, accessibility, and visual preservation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..core.field_extractor import FormField, FieldExtractor
from ..core.pdf_analyzer import PDFAnalyzer
from ..utils.logging import get_logger
from ..utils.errors import PDFProcessingError

logger = get_logger(__name__)


@dataclass
class StructureValidation:
    """Result of PDF structure validation."""
    is_valid: bool
    pdf_version: str
    object_count: int
    page_count: int
    form_present: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class FunctionalityValidation:
    """Result of form functionality validation."""
    form_functional: bool
    field_count_match: bool
    all_fields_accessible: bool
    missing_fields: List[str]
    broken_functionality: List[str]
    preserved_properties: int
    total_properties_checked: int


@dataclass
class AccessibilityValidation:
    """Result of accessibility validation."""
    tab_order_preserved: bool
    field_labels_present: bool
    screen_reader_compatible: bool
    keyboard_navigation: bool
    accessibility_issues: List[str]
    accessibility_warnings: List[str]


@dataclass
class VisualValidation:
    """Result of visual appearance validation."""
    layout_preserved: bool
    coordinates_unchanged: bool
    field_sizes_preserved: bool
    visual_differences: List[str]
    coordinate_variations: List[Dict[str, Any]]


@dataclass
class IntegrityReport:
    """Comprehensive integrity validation report."""
    overall_status: str  # 'excellent', 'good', 'acceptable', 'poor', 'critical'
    safety_score: float  # 0.0 - 1.0
    structure_validation: StructureValidation
    functionality_validation: FunctionalityValidation
    accessibility_validation: AccessibilityValidation
    visual_validation: VisualValidation
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    validation_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_status": self.overall_status,
            "safety_score": self.safety_score,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "structure_validation": {
                "is_valid": self.structure_validation.is_valid,
                "pdf_version": self.structure_validation.pdf_version,
                "object_count": self.structure_validation.object_count,
                "page_count": self.structure_validation.page_count,
                "form_present": self.structure_validation.form_present,
                "errors": self.structure_validation.errors,
                "warnings": self.structure_validation.warnings
            },
            "functionality_validation": {
                "form_functional": self.functionality_validation.form_functional,
                "field_count_match": self.functionality_validation.field_count_match,
                "all_fields_accessible": self.functionality_validation.all_fields_accessible,
                "missing_fields": self.functionality_validation.missing_fields,
                "broken_functionality": self.functionality_validation.broken_functionality,
                "preserved_properties": self.functionality_validation.preserved_properties,
                "total_properties_checked": self.functionality_validation.total_properties_checked
            },
            "accessibility_validation": {
                "tab_order_preserved": self.accessibility_validation.tab_order_preserved,
                "field_labels_present": self.accessibility_validation.field_labels_present,
                "screen_reader_compatible": self.accessibility_validation.screen_reader_compatible,
                "keyboard_navigation": self.accessibility_validation.keyboard_navigation,
                "accessibility_issues": self.accessibility_validation.accessibility_issues,
                "accessibility_warnings": self.accessibility_validation.accessibility_warnings
            },
            "visual_validation": {
                "layout_preserved": self.visual_validation.layout_preserved,
                "coordinates_unchanged": self.visual_validation.coordinates_unchanged,
                "field_sizes_preserved": self.visual_validation.field_sizes_preserved,
                "visual_differences": self.visual_validation.visual_differences,
                "coordinate_variations": self.visual_validation.coordinate_variations
            },
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations
        }


class PDFIntegrityValidator:
    """Validate PDF integrity after field modifications."""
    
    def __init__(self):
        """Initialize PDF integrity validator."""
        logger.info("PDFIntegrityValidator initialized")
    
    def validate_pdf_structure(self, pdf_path: str) -> StructureValidation:
        """
        Validate basic PDF structure integrity.
        
        Args:
            pdf_path: Path to PDF file to validate
            
        Returns:
            StructureValidation with validation results
        """
        logger.info(f"Validating PDF structure: {pdf_path}")
        
        errors = []
        warnings = []
        is_valid = True
        pdf_version = ""
        object_count = 0
        page_count = 0
        form_present = False
        
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                errors.append(f"PDF file not found: {pdf_path}")
                is_valid = False
            else:
                # Basic file checks
                if pdf_path.stat().st_size == 0:
                    errors.append("PDF file is empty")
                    is_valid = False
                
                # Read PDF structure
                try:
                    with open(pdf_path, 'rb') as f:
                        reader = PdfReader(f)
                        
                        # Check PDF version
                        if hasattr(reader, 'pdf_header'):
                            pdf_version = reader.pdf_header
                        else:
                            # Fallback: read header manually
                            f.seek(0)
                            header = f.read(8).decode('ascii', errors='ignore')
                            if header.startswith('%PDF-'):
                                pdf_version = header
                            else:
                                errors.append("Invalid PDF header")
                                is_valid = False
                        
                        # Check basic properties
                        try:
                            page_count = len(reader.pages)
                            if page_count == 0:
                                errors.append("PDF has no pages")
                                is_valid = False
                        except Exception as e:
                            errors.append(f"Cannot read PDF pages: {e}")
                            is_valid = False
                        
                        # Check object count
                        try:
                            if hasattr(reader, '_objects'):
                                object_count = len(reader._objects)
                            elif hasattr(reader, 'xref'):
                                object_count = len(reader.xref)
                        except Exception as e:
                            warnings.append(f"Cannot count PDF objects: {e}")
                        
                        # Check for form fields
                        try:
                            if reader.trailer.get("/Root"):
                                root = reader.trailer["/Root"]
                                if root.get("/AcroForm"):
                                    form_present = True
                                    acro_form = root["/AcroForm"]
                                    if not acro_form.get("/Fields"):
                                        warnings.append("AcroForm present but no fields found")
                        except Exception as e:
                            warnings.append(f"Cannot check form presence: {e}")
                        
                        # Validate cross-reference table
                        try:
                            # Try to access metadata to validate xref
                            _ = reader.metadata
                        except Exception as e:
                            errors.append(f"Cross-reference table validation failed: {e}")
                            is_valid = False
                
                except PdfReadError as e:
                    errors.append(f"PDF read error: {e}")
                    is_valid = False
                except Exception as e:
                    errors.append(f"Unexpected error reading PDF: {e}")
                    is_valid = False
        
        except Exception as e:
            errors.append(f"Structure validation error: {e}")
            is_valid = False
        
        validation = StructureValidation(
            is_valid=is_valid,
            pdf_version=pdf_version,
            object_count=object_count,
            page_count=page_count,
            form_present=form_present,
            errors=errors,
            warnings=warnings
        )
        
        logger.info(f"Structure validation complete: {'valid' if is_valid else 'invalid'}")
        return validation
    
    def validate_form_functionality(self, pdf_path: str, 
                                  original_fields: List[FormField]) -> FunctionalityValidation:
        """
        Validate form functionality preservation.
        
        Args:
            pdf_path: Path to modified PDF
            original_fields: Original form fields for comparison
            
        Returns:
            FunctionalityValidation with validation results
        """
        logger.info(f"Validating form functionality: {pdf_path}")
        
        form_functional = True
        field_count_match = True
        all_fields_accessible = True
        missing_fields = []
        broken_functionality = []
        preserved_properties = 0
        total_properties_checked = 0
        
        try:
            # Analyze modified PDF
            analyzer = PDFAnalyzer(pdf_path)
            
            if not analyzer.has_form_fields():
                form_functional = False
                broken_functionality.append("No form fields found in modified PDF")
            else:
                # Extract fields from modified PDF
                extractor = FieldExtractor(analyzer)
                modified_fields = extractor.extract_form_fields()
                
                # Check field count
                if len(modified_fields) != len(original_fields):
                    field_count_match = False
                    broken_functionality.append(
                        f"Field count mismatch: expected {len(original_fields)}, "
                        f"found {len(modified_fields)}"
                    )
                
                # Create lookup for comparison
                original_by_id = {field.id: field for field in original_fields}
                modified_by_id = {field.id: field for field in modified_fields}
                
                # Check for missing fields
                for original_field in original_fields:
                    if original_field.id not in modified_by_id:
                        missing_fields.append(original_field.id)
                        all_fields_accessible = False
                
                # Validate preserved properties
                for original_field in original_fields:
                    if original_field.id in modified_by_id:
                        modified_field = modified_by_id[original_field.id]
                        
                        # Check critical properties
                        properties_to_check = [
                            ('field_type', 'Field type'),
                            ('page', 'Page number'),
                            ('rect', 'Coordinates'),
                            ('value', 'Field value'),
                            ('parent', 'Parent relationship'),
                            ('children', 'Children relationships')
                        ]
                        
                        for prop_name, prop_desc in properties_to_check:
                            total_properties_checked += 1
                            
                            original_value = getattr(original_field, prop_name)
                            modified_value = getattr(modified_field, prop_name)
                            
                            # Special handling for coordinates (allow small variations)
                            if prop_name == 'rect':
                                if self._coordinates_match(original_value, modified_value):
                                    preserved_properties += 1
                                else:
                                    broken_functionality.append(
                                        f"Field {original_field.id}: {prop_desc} changed significantly"
                                    )
                            else:
                                if original_value == modified_value:
                                    preserved_properties += 1
                                else:
                                    # Only report as broken if it's a critical property
                                    if prop_name in ['field_type', 'page']:
                                        broken_functionality.append(
                                            f"Field {original_field.id}: {prop_desc} changed"
                                        )
                
                # Check for JavaScript functionality preservation
                try:
                    if analyzer.reader.trailer.get("/Root"):
                        root = analyzer.reader.trailer["/Root"]
                        if root.get("/AcroForm"):
                            acro_form = root["/AcroForm"]
                            if acro_form.get("/CO") or acro_form.get("/DR"):
                                # Form has calculation order or default resources
                                logger.info("Form has advanced features (JavaScript/calculations)")
                                # TODO: More detailed JavaScript validation
                except Exception as e:
                    logger.warning(f"Could not check JavaScript functionality: {e}")
        
        except Exception as e:
            form_functional = False
            broken_functionality.append(f"Functionality validation error: {e}")
            logger.error(f"Form functionality validation failed: {e}")
        
        validation = FunctionalityValidation(
            form_functional=form_functional,
            field_count_match=field_count_match,
            all_fields_accessible=all_fields_accessible,
            missing_fields=missing_fields,
            broken_functionality=broken_functionality,
            preserved_properties=preserved_properties,
            total_properties_checked=total_properties_checked
        )
        
        logger.info(f"Functionality validation complete: {'functional' if form_functional else 'broken'}")
        return validation
    
    def validate_field_accessibility(self, pdf_path: str) -> AccessibilityValidation:
        """
        Validate field accessibility after modifications.
        
        Args:
            pdf_path: Path to modified PDF
            
        Returns:
            AccessibilityValidation with validation results
        """
        logger.info(f"Validating field accessibility: {pdf_path}")
        
        tab_order_preserved = True
        field_labels_present = True
        screen_reader_compatible = True
        keyboard_navigation = True
        accessibility_issues = []
        accessibility_warnings = []
        
        try:
            analyzer = PDFAnalyzer(pdf_path)
            
            if analyzer.has_form_fields():
                extractor = FieldExtractor(analyzer)
                fields = extractor.extract_form_fields()
                
                # Check field labels
                unlabeled_fields = 0
                for field in fields:
                    if not field.name or field.name.strip() == "":
                        unlabeled_fields += 1
                        field_labels_present = False
                
                if unlabeled_fields > 0:
                    accessibility_issues.append(f"{unlabeled_fields} fields without proper labels")
                
                # Check tab order (basic validation)
                try:
                    # Check if form has tab order information
                    if analyzer.reader.trailer.get("/Root"):
                        root = analyzer.reader.trailer["/Root"]
                        if root.get("/AcroForm"):
                            acro_form = root["/AcroForm"]
                            if not acro_form.get("/CO"):  # Calculation Order which affects tab order
                                accessibility_warnings.append("No explicit tab order defined")
                except Exception as e:
                    accessibility_warnings.append(f"Could not check tab order: {e}")
                
                # Check for accessibility attributes
                fields_with_tooltips = 0
                for field in fields:
                    # Check if field has tooltip/alternative text in properties
                    if field.properties and field.properties.get('TU'):  # Tooltip/Alternative description
                        fields_with_tooltips += 1
                
                if fields_with_tooltips == 0 and len(fields) > 0:
                    accessibility_warnings.append("No fields have tooltips or alternative descriptions")
                
                # Check for screen reader compatibility markers
                try:
                    # Look for structure tree or tagged PDF markers
                    if analyzer.reader.trailer.get("/Root"):
                        root = analyzer.reader.trailer["/Root"]
                        if not root.get("/StructTreeRoot") and not root.get("/MarkInfo"):
                            accessibility_warnings.append("PDF not tagged for screen readers")
                            screen_reader_compatible = False
                except Exception as e:
                    accessibility_warnings.append(f"Could not check screen reader compatibility: {e}")
            
            else:
                accessibility_issues.append("No form fields found for accessibility validation")
                field_labels_present = False
                tab_order_preserved = False
                keyboard_navigation = False
                screen_reader_compatible = False
        
        except Exception as e:
            accessibility_issues.append(f"Accessibility validation error: {e}")
            logger.error(f"Accessibility validation failed: {e}")
        
        validation = AccessibilityValidation(
            tab_order_preserved=tab_order_preserved,
            field_labels_present=field_labels_present,
            screen_reader_compatible=screen_reader_compatible,
            keyboard_navigation=keyboard_navigation,
            accessibility_issues=accessibility_issues,
            accessibility_warnings=accessibility_warnings
        )
        
        logger.info(f"Accessibility validation complete")
        return validation
    
    def validate_visual_appearance(self, original_pdf: str, modified_pdf: str) -> VisualValidation:
        """
        Validate visual appearance preservation.
        
        Args:
            original_pdf: Path to original PDF
            modified_pdf: Path to modified PDF
            
        Returns:
            VisualValidation with validation results
        """
        logger.info(f"Validating visual appearance preservation")
        
        layout_preserved = True
        coordinates_unchanged = True
        field_sizes_preserved = True
        visual_differences = []
        coordinate_variations = []
        
        try:
            # Analyze both PDFs
            original_analyzer = PDFAnalyzer(original_pdf)
            modified_analyzer = PDFAnalyzer(modified_pdf)
            
            if original_analyzer.has_form_fields() and modified_analyzer.has_form_fields():
                original_extractor = FieldExtractor(original_analyzer)
                modified_extractor = FieldExtractor(modified_analyzer)
                
                original_fields = original_extractor.extract_form_fields()
                modified_fields = modified_extractor.extract_form_fields()
                
                # Create lookup by field ID
                original_by_id = {field.id: field for field in original_fields}
                modified_by_id = {field.id: field for field in modified_fields}
                
                # Compare coordinates and sizes
                for field_id, original_field in original_by_id.items():
                    if field_id in modified_by_id:
                        modified_field = modified_by_id[field_id]
                        
                        # Compare coordinates
                        if not self._coordinates_match(original_field.rect, modified_field.rect):
                            coordinates_unchanged = False
                            coordinate_variations.append({
                                "field_id": field_id,
                                "original_coordinates": original_field.rect,
                                "modified_coordinates": modified_field.rect,
                                "difference": self._calculate_coordinate_difference(
                                    original_field.rect, modified_field.rect
                                )
                            })
                        
                        # Compare page placement
                        if original_field.page != modified_field.page:
                            layout_preserved = False
                            visual_differences.append(
                                f"Field {field_id} moved from page {original_field.page} "
                                f"to page {modified_field.page}"
                            )
                        
                        # Compare field sizes
                        original_size = self._calculate_field_size(original_field.rect)
                        modified_size = self._calculate_field_size(modified_field.rect)
                        
                        if not self._sizes_match(original_size, modified_size):
                            field_sizes_preserved = False
                            visual_differences.append(
                                f"Field {field_id} size changed: {original_size} -> {modified_size}"
                            )
                
                # Check page count consistency
                original_page_count = len(original_analyzer.reader.pages)
                modified_page_count = len(modified_analyzer.reader.pages)
                
                if original_page_count != modified_page_count:
                    layout_preserved = False
                    visual_differences.append(
                        f"Page count changed: {original_page_count} -> {modified_page_count}"
                    )
            
            else:
                visual_differences.append("Form fields missing in one or both PDFs")
                layout_preserved = False
        
        except Exception as e:
            visual_differences.append(f"Visual validation error: {e}")
            layout_preserved = False
            logger.error(f"Visual appearance validation failed: {e}")
        
        validation = VisualValidation(
            layout_preserved=layout_preserved,
            coordinates_unchanged=coordinates_unchanged,
            field_sizes_preserved=field_sizes_preserved,
            visual_differences=visual_differences,
            coordinate_variations=coordinate_variations
        )
        
        logger.info(f"Visual validation complete: layout {'preserved' if layout_preserved else 'changed'}")
        return validation
    
    def generate_integrity_report(self, pdf_path: str, 
                                original_fields: Optional[List[FormField]] = None,
                                original_pdf: Optional[str] = None) -> IntegrityReport:
        """
        Generate comprehensive integrity report.
        
        Args:
            pdf_path: Path to modified PDF
            original_fields: Original form fields for comparison
            original_pdf: Path to original PDF for visual comparison
            
        Returns:
            IntegrityReport with comprehensive validation results
        """
        logger.info(f"Generating comprehensive integrity report for: {pdf_path}")
        
        # Run all validations
        structure_validation = self.validate_pdf_structure(pdf_path)
        
        functionality_validation = FunctionalityValidation(
            form_functional=True, field_count_match=True, all_fields_accessible=True,
            missing_fields=[], broken_functionality=[], preserved_properties=0,
            total_properties_checked=0
        )
        if original_fields:
            functionality_validation = self.validate_form_functionality(pdf_path, original_fields)
        
        accessibility_validation = self.validate_field_accessibility(pdf_path)
        
        visual_validation = VisualValidation(
            layout_preserved=True, coordinates_unchanged=True, field_sizes_preserved=True,
            visual_differences=[], coordinate_variations=[]
        )
        if original_pdf:
            visual_validation = self.validate_visual_appearance(original_pdf, pdf_path)
        
        # Calculate overall status and safety score
        critical_issues = []
        warnings = []
        recommendations = []
        
        # Collect critical issues
        if not structure_validation.is_valid:
            critical_issues.extend(structure_validation.errors)
        
        if not functionality_validation.form_functional:
            critical_issues.extend(functionality_validation.broken_functionality)
        
        critical_issues.extend(accessibility_validation.accessibility_issues)
        
        if not visual_validation.layout_preserved:
            critical_issues.extend(visual_validation.visual_differences)
        
        # Collect warnings
        warnings.extend(structure_validation.warnings)
        warnings.extend(accessibility_validation.accessibility_warnings)
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(
            structure_validation, functionality_validation, 
            accessibility_validation, visual_validation
        )
        
        # Determine overall status
        overall_status = self._determine_overall_status(safety_score, critical_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            structure_validation, functionality_validation,
            accessibility_validation, visual_validation, safety_score
        )
        
        report = IntegrityReport(
            overall_status=overall_status,
            safety_score=safety_score,
            structure_validation=structure_validation,
            functionality_validation=functionality_validation,
            accessibility_validation=accessibility_validation,
            visual_validation=visual_validation,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
            validation_timestamp=datetime.now()
        )
        
        logger.info(f"Integrity report generated: {overall_status} (safety score: {safety_score:.2f})")
        return report
    
    def _coordinates_match(self, coord1: List[float], coord2: List[float], 
                         tolerance: float = 1.0) -> bool:
        """
        Check if coordinates match within tolerance.
        
        Args:
            coord1: First coordinate set [x1, y1, x2, y2]
            coord2: Second coordinate set [x1, y1, x2, y2]
            tolerance: Tolerance for coordinate differences
            
        Returns:
            True if coordinates match within tolerance
        """
        if len(coord1) != 4 or len(coord2) != 4:
            return False
        
        for i in range(4):
            if abs(coord1[i] - coord2[i]) > tolerance:
                return False
        
        return True
    
    def _calculate_coordinate_difference(self, coord1: List[float], coord2: List[float]) -> Dict[str, float]:
        """
        Calculate coordinate differences.
        
        Args:
            coord1: First coordinate set
            coord2: Second coordinate set
            
        Returns:
            Dictionary with coordinate differences
        """
        if len(coord1) != 4 or len(coord2) != 4:
            return {"error": "Invalid coordinates"}
        
        return {
            "x1_diff": abs(coord1[0] - coord2[0]),
            "y1_diff": abs(coord1[1] - coord2[1]),
            "x2_diff": abs(coord1[2] - coord2[2]),
            "y2_diff": abs(coord1[3] - coord2[3]),
            "max_diff": max(abs(coord1[i] - coord2[i]) for i in range(4))
        }
    
    def _calculate_field_size(self, coordinates: List[float]) -> Tuple[float, float]:
        """
        Calculate field size from coordinates.
        
        Args:
            coordinates: Field coordinates [x1, y1, x2, y2]
            
        Returns:
            Tuple of (width, height)
        """
        if len(coordinates) != 4:
            return (0.0, 0.0)
        
        width = abs(coordinates[2] - coordinates[0])
        height = abs(coordinates[3] - coordinates[1])
        return (width, height)
    
    def _sizes_match(self, size1: Tuple[float, float], size2: Tuple[float, float], 
                    tolerance: float = 1.0) -> bool:
        """
        Check if sizes match within tolerance.
        
        Args:
            size1: First size (width, height)
            size2: Second size (width, height)
            tolerance: Tolerance for size differences
            
        Returns:
            True if sizes match within tolerance
        """
        return (abs(size1[0] - size2[0]) <= tolerance and 
                abs(size1[1] - size2[1]) <= tolerance)
    
    def _calculate_safety_score(self, structure: StructureValidation,
                              functionality: FunctionalityValidation,
                              accessibility: AccessibilityValidation,
                              visual: VisualValidation) -> float:
        """
        Calculate overall safety score.
        
        Args:
            structure: Structure validation results
            functionality: Functionality validation results  
            accessibility: Accessibility validation results
            visual: Visual validation results
            
        Returns:
            Safety score from 0.0 to 1.0
        """
        score = 1.0
        
        # Structure validation (30% weight)
        if not structure.is_valid:
            score -= 0.30
        elif structure.warnings:
            score -= 0.05 * min(len(structure.warnings), 6)  # Max 30% reduction
        
        # Functionality validation (40% weight)
        if not functionality.form_functional:
            score -= 0.40
        elif not functionality.field_count_match:
            score -= 0.20
        elif functionality.broken_functionality:
            score -= 0.10 * min(len(functionality.broken_functionality), 4)  # Max 40% reduction
        
        # Accessibility validation (15% weight)
        if accessibility.accessibility_issues:
            score -= 0.03 * min(len(accessibility.accessibility_issues), 5)  # Max 15% reduction
        
        # Visual validation (15% weight)
        if not visual.layout_preserved:
            score -= 0.10
        elif not visual.coordinates_unchanged:
            score -= 0.05
        
        return max(0.0, min(1.0, score))
    
    def _determine_overall_status(self, safety_score: float, critical_issues: List[str]) -> str:
        """
        Determine overall status based on safety score and issues.
        
        Args:
            safety_score: Calculated safety score
            critical_issues: List of critical issues
            
        Returns:
            Overall status string
        """
        if len(critical_issues) > 5 or safety_score < 0.3:
            return "critical"
        elif len(critical_issues) > 2 or safety_score < 0.6:
            return "poor"
        elif len(critical_issues) > 0 or safety_score < 0.8:
            return "acceptable"
        elif safety_score < 0.95:
            return "good"
        else:
            return "excellent"
    
    def _generate_recommendations(self, structure: StructureValidation,
                                functionality: FunctionalityValidation,
                                accessibility: AccessibilityValidation,
                                visual: VisualValidation,
                                safety_score: float) -> List[str]:
        """
        Generate recommendations based on validation results.
        
        Args:
            structure: Structure validation results
            functionality: Functionality validation results
            accessibility: Accessibility validation results
            visual: Visual validation results
            safety_score: Calculated safety score
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not structure.is_valid:
            recommendations.append("Critical: Fix PDF structure issues before use")
        
        if not functionality.form_functional:
            recommendations.append("Critical: Restore form functionality")
        
        if functionality.missing_fields:
            recommendations.append(f"Restore {len(functionality.missing_fields)} missing fields")
        
        if accessibility.accessibility_issues:
            recommendations.append("Improve accessibility for screen readers and keyboard navigation")
        
        if not visual.layout_preserved:
            recommendations.append("Review visual layout changes for user impact")
        
        if safety_score < 0.8:
            recommendations.append("Consider rollback or additional fixes before production use")
        
        if safety_score >= 0.95:
            recommendations.append("Validation passed - PDF ready for production use")
        
        return recommendations