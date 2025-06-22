#!/usr/bin/env python3
"""
Field Extractor - Form field discovery and extraction functionality

This module provides the FieldExtractor class for discovering and extracting
form fields from PDF documents, along with the FormField data class for
structured field information.
"""

from dataclasses import dataclass, field as dataclass_field
from typing import List, Any, Dict, Optional, Union
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject

from .pdf_analyzer import PDFAnalyzer
from .constants import FieldExtractionConstants, PDFConstants
from ..utils.errors import PDFProcessingError
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FormField:
    """
    Represents a form field extracted from a PDF document.
    
    Contains all essential properties of a form field including
    identification, type, location, and various metadata.
    """
    
    id: str
    name: str
    field_type: str  # 'text', 'checkbox', 'radio', 'choice', 'signature', 'button'
    page: int
    rect: List[float]  # [x1, y1, x2, y2] - field coordinates
    value: Any
    properties: Dict[str, Any]
    parent: Optional[str] = None
    children: List[str] = dataclass_field(default_factory=list)
    
    def __post_init__(self):
        """Validate field data after initialization."""
        if not self.name:
            self.name = f"Field_{self.id}"
        
        # Ensure rect has 4 coordinates
        if len(self.rect) != 4:
            logger.warning(f"Field {self.id}: Invalid rect coordinates, using defaults")
            self.rect = [FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT, 
                        FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT]
        
        # Ensure properties is a dict
        if not isinstance(self.properties, dict):
            self.properties = {}
    
    @property
    def width(self) -> float:
        """Get field width from coordinates."""
        return abs(self.rect[2] - self.rect[0])
    
    @property
    def height(self) -> float:
        """Get field height from coordinates."""
        return abs(self.rect[3] - self.rect[1])
    
    @property
    def is_required(self) -> bool:
        """Check if field is required."""
        return self.properties.get("required", False)
    
    @property
    def is_readonly(self) -> bool:
        """Check if field is read-only."""
        return self.properties.get("readonly", False)
    
    @property
    def coordinates(self) -> Dict[str, float]:
        """Get coordinates as a dictionary for compatibility."""
        return {
            'x': self.rect[0],
            'y': self.rect[1],
            'width': self.width,
            'height': self.height
        }


class FieldExtractor:
    """
    Extracts form fields from PDF documents.
    
    This class works with PDFAnalyzer to discover and extract form fields
    from PDF AcroForm dictionaries, providing structured access to field
    information including type, location, and properties.
    """
    
    def __init__(self, pdf_analyzer: PDFAnalyzer):
        """
        Initialize FieldExtractor with a PDFAnalyzer instance.
        
        Args:
            pdf_analyzer: Initialized PDFAnalyzer instance
            
        Raises:
            PDFProcessingError: If PDF analyzer is invalid
        """
        if not pdf_analyzer or not pdf_analyzer.reader:
            raise PDFProcessingError("Invalid PDFAnalyzer instance - reader not available")
        
        self.pdf_analyzer = pdf_analyzer
        self.reader = pdf_analyzer.reader
        self._field_cache: Optional[List[FormField]] = None
        
        logger.info(f"FieldExtractor initialized for: {pdf_analyzer.file_path}")
    
    def extract_form_fields(self, force_refresh: bool = False) -> List[FormField]:
        """
        Extract all form fields from PDF.
        
        Args:
            force_refresh: If True, bypass cache and re-extract fields
            
        Returns:
            List of FormField objects representing all fields in the PDF
        """
        # Return cached fields if available and not forcing refresh
        if self._field_cache and not force_refresh:
            logger.info(f"Returning {len(self._field_cache)} cached form fields")
            return self._field_cache
        
        fields = []
        
        try:
            # Check if PDF has form fields
            if not self.pdf_analyzer.has_form_fields():
                logger.info("PDF has no form fields")
                self._field_cache = fields
                return fields
            
            # Get AcroForm dictionary with safe access
            catalog = self.reader.trailer.get("/Root")
            if not catalog:
                logger.warning("No document catalog found")
                self._field_cache = fields
                return fields
            
            acro_form = catalog.get("/AcroForm")
            if not acro_form:
                logger.warning("No AcroForm found in catalog")
                self._field_cache = fields
                return fields
            
            # Extract fields from AcroForm
            if "/Fields" in acro_form:
                field_array = acro_form["/Fields"]
                logger.info(f"Found {len(field_array)} form fields in PDF")
                
                # Large form memory management
                if len(field_array) > FieldExtractionConstants.LARGE_FORM_THRESHOLD:
                    logger.warning(f"Large form detected ({len(field_array)} fields), consider chunked processing")
                
                field_counter = 0
                for i, field_ref in enumerate(field_array):
                    try:
                        field_obj = field_ref.get_object() if isinstance(field_ref, IndirectObject) else field_ref
                        if isinstance(field_obj, DictionaryObject):
                            # Parse field and any child fields (for radio button groups)
                            parsed_fields = self._parse_field_hierarchy(field_obj, field_counter, set())
                            for field in parsed_fields:
                                if field:
                                    fields.append(field)
                                    logger.debug(f"Extracted field: {field.name} ({field.field_type})")
                            field_counter += len(parsed_fields)
                    except Exception as e:
                        logger.error(f"Error parsing field {i}: {str(e)}")
                        continue
            
            logger.info(f"Successfully extracted {len(fields)} form fields")
            self._field_cache = fields
            return fields
            
        except Exception as e:
            logger.error(f"Error extracting form fields: {str(e)}")
            raise PDFProcessingError(f"Failed to extract form fields: {str(e)}")
    
    def _parse_field_hierarchy(self, field_obj: DictionaryObject, index: int, 
                              visited_refs: Optional[set] = None) -> List[FormField]:
        """
        Parse field hierarchy including child fields for radio button groups.
        
        Args:
            field_obj: PDF field dictionary object
            index: Field index for ID generation
            visited_refs: Set of visited references to prevent circular references
            
        Returns:
            List of FormField instances (may be empty)
        """
        if visited_refs is None:
            visited_refs = set()
        
        # Get object reference to detect cycles
        obj_ref = getattr(field_obj, 'indirect_reference', None)
        if obj_ref and obj_ref in visited_refs:
            logger.warning(f"Circular reference detected in field hierarchy: {obj_ref}")
            return []
        
        if obj_ref:
            visited_refs.add(obj_ref)
        
        fields = []
        
        try:
            # Check if this field has children (like radio button groups)
            if "/Kids" in field_obj:
                kids = field_obj["/Kids"]
                if isinstance(kids, (list, ArrayObject)) and len(kids) > 0:
                    # This is a parent field with children (likely radio group)
                    parent_name = self._get_field_name(field_obj, index)
                    logger.debug(f"Found parent field '{parent_name}' with {len(kids)} children")
                    
                    # Parse each child field
                    for child_index, kid_ref in enumerate(kids):
                        try:
                            kid_obj = kid_ref.get_object() if isinstance(kid_ref, IndirectObject) else kid_ref
                            if isinstance(kid_obj, DictionaryObject):
                                # Use string-based ID to prevent integer overflow
                                child_id_index = f"{index}_{child_index}"
                                child_field = self._parse_field(kid_obj, child_id_index)
                                if child_field:
                                    # Set parent relationship
                                    child_field.parent = parent_name
                                    
                                    # Improve child field naming for radio buttons
                                    if child_field.field_type in ["radio", "checkbox"]:
                                        # Try to get the export value for better naming
                                        export_value = self._get_field_export_value(kid_obj)
                                        if export_value and export_value != child_field.name:
                                            child_field.name = f"{parent_name}__{export_value}"
                                        elif child_field.name.startswith("Field_"):
                                            child_field.name = f"{parent_name}__option_{child_index}"
                                    
                                    fields.append(child_field)
                                    logger.debug(f"Extracted child field: {child_field.name} (parent: {parent_name})")
                        except Exception as e:
                            logger.warning(f"Error parsing child field {child_index} of {parent_name}: {str(e)}")
                            continue
                    
                    # If we found children, ALSO include the parent as a separate field
                    # Both the group (parent) and individual widgets (children) are valid fields
                    if fields:
                        # Add the parent group as a field too
                        parent_field = self._parse_field(field_obj, index)
                        if parent_field:
                            # Mark this as a parent group
                            parent_field.properties["is_group_container"] = True
                            fields.insert(0, parent_field)  # Add parent first
                        return fields
            
            # No children or no valid children found - parse as regular field
            field = self._parse_field(field_obj, index)
            if field:
                fields.append(field)
                
        except Exception as e:
            logger.error(f"Error parsing field hierarchy {index}: {str(e)}")
        
        return fields
    
    def _parse_field(self, field_obj: DictionaryObject, index: Union[int, str]) -> Optional[FormField]:
        """
        Parse individual field object into FormField instance.
        
        Args:
            field_obj: PDF field dictionary object
            index: Field index for ID generation (int or string)
            
        Returns:
            FormField instance or None if parsing fails
        """
        try:
            # Extract basic field properties
            field_name = self._get_field_name(field_obj, index)
            field_type = self._determine_field_type(field_obj)
            field_value = self._get_field_value(field_obj)
            field_rect = self._get_field_rect(field_obj)
            page_num = self._find_field_page(field_obj)
            
            # Extract field properties and flags
            properties = self._extract_field_properties(field_obj)
            
            # Create field ID - handle both int and string indices
            if isinstance(index, int):
                field_id = f"field_{index:06d}"
            else:
                field_id = f"field_{index}"
            
            return FormField(
                id=field_id,
                name=field_name,
                field_type=field_type,
                page=page_num,
                rect=field_rect,
                value=field_value,
                properties=properties
            )
            
        except Exception as e:
            logger.error(f"Error parsing field {index}: {str(e)}")
            return None
    
    def _get_field_name(self, field_obj: DictionaryObject, index: Union[int, str]) -> str:
        """Extract field name from field object."""
        try:
            # Try partial name first (/T), then full name (/TU)
            name_value = field_obj.get("/T")
            if name_value is not None:
                name = str(name_value) if name_value else ""
                return name if name else f"Field_{index}"
            
            # Try full name as fallback
            name_value = field_obj.get("/TU")
            if name_value is not None:
                name = str(name_value) if name_value else ""
                return name if name else f"Field_{index}"
            
            return f"Field_{index}"
        except Exception:
            return f"Field_{index}"
    
    def _determine_field_type(self, field_obj: DictionaryObject) -> str:
        """
        Determine the type of form field.
        
        PDF field types:
        - /Tx: Text field
        - /Btn: Button field (checkbox, radio, pushbutton)
        - /Ch: Choice field (dropdown, listbox)
        - /Sig: Signature field
        """
        try:
            ft = field_obj.get("/FT")
            
            if ft == "/Tx":
                return "text"
            elif ft == "/Btn":
                # Distinguish between checkbox, radio, and pushbutton
                ff = field_obj.get("/Ff", 0)
                if isinstance(ff, int):
                    # Bit 16 (32768): Radio button
                    if ff & 32768:
                        return "radio"
                    # Bit 15 (16384): Pushbutton
                    elif ff & 16384:
                        return "button"
                    else:
                        return "checkbox"
                else:
                    return "checkbox"  # Default for button fields
            elif ft == "/Ch":
                # Could be dropdown or listbox
                ff = field_obj.get("/Ff", 0)
                if isinstance(ff, int) and (ff & 131072):  # Bit 18: Combo
                    return "dropdown"
                else:
                    return "listbox"
            elif ft == "/Sig":
                return "signature"
            elif ft is None:
                # Widget annotation without explicit field type
                # Check if it has appearance states (likely radio/checkbox)
                if "/AP" in field_obj:
                    ap = field_obj["/AP"]
                    if isinstance(ap, DictionaryObject) and "/N" in ap:
                        normal_ap = ap["/N"]
                        if isinstance(normal_ap, DictionaryObject):
                            # If it has /Off state, it's likely a radio button or checkbox
                            states = list(normal_ap.keys())
                            if any(str(state) in ["/Off", "/No"] for state in states):
                                # Default to radio for widget annotations (most common case)
                                return "radio"
                
                # Check if it's a widget annotation
                if "/Subtype" in field_obj and field_obj.get("/Subtype") == "/Widget":
                    return "radio"  # Most widget annotations are radio buttons
                
                return "unknown"
            else:
                logger.warning(f"Unknown field type: {ft}")
                return "unknown"
                
        except Exception as e:
            logger.warning(f"Error determining field type: {str(e)}")
            return "unknown"
    
    def _get_field_value(self, field_obj: DictionaryObject) -> Any:
        """Extract field value."""
        try:
            value = field_obj.get("/V")
            if value is not None:
                return str(value)
            # Try default value if no current value
            default_value = field_obj.get("/DV")
            return str(default_value) if default_value is not None else ""
        except Exception:
            return ""
    
    def _get_field_rect(self, field_obj: DictionaryObject) -> List[float]:
        """Extract field rectangle coordinates."""
        try:
            rect = field_obj.get("/Rect")
            if not rect or len(rect) < 4:
                logger.warning("Invalid field rectangle - insufficient coordinates")
                return [FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT,
                       FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT]
            
            try:
                return [float(rect[i]) for i in range(4)]
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid coordinate values in rect: {e}")
                return [FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT,
                       FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT]
        except Exception as e:
            logger.warning(f"Error extracting field rectangle: {str(e)}")
            return [FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT,
                   FieldExtractionConstants.DEFAULT_FIELD_WIDTH, FieldExtractionConstants.DEFAULT_FIELD_HEIGHT]
    
    def _find_field_page(self, field_obj: DictionaryObject) -> int:
        """
        Find which page contains this field.
        
        This is a simplified implementation. In practice, you'd need to
        traverse the page tree and check for widget annotations.
        """
        try:
            # Check if field has page reference
            if "/P" in field_obj:
                # Field references its page directly
                page_ref = field_obj["/P"]
                if isinstance(page_ref, IndirectObject):
                    # Find this page in the pages array
                    for i, page in enumerate(self.reader.pages):
                        if page.indirect_reference == page_ref:
                            return i + 1
            
            # Fallback: check all pages for widget annotations
            # This is more complex and resource-intensive
            for page_num, page in enumerate(self.reader.pages, 1):
                if "/Annots" in page:
                    annotations = page["/Annots"]
                    if isinstance(annotations, ArrayObject):
                        for annot_ref in annotations:
                            try:
                                annot = annot_ref.get_object() if isinstance(annot_ref, IndirectObject) else annot_ref
                                if isinstance(annot, DictionaryObject):
                                    # Check if this annotation references our field
                                    if "/Parent" in annot and annot["/Parent"] == field_obj:
                                        return page_num
                            except Exception:
                                continue
            
            # Default to page 1 if we can't determine the page
            return 1
            
        except Exception as e:
            logger.warning(f"Error finding field page: {str(e)}")
            return 1
    
    def _extract_field_properties(self, field_obj: DictionaryObject) -> Dict[str, Any]:
        """Extract field properties and flags."""
        properties = {}
        
        try:
            # Extract field flags (/Ff)
            ff = field_obj.get("/Ff", 0)
            if isinstance(ff, int):
                properties.update({
                    "readonly": bool(ff & PDFConstants.READONLY_FLAG),
                    "required": bool(ff & PDFConstants.REQUIRED_FLAG),
                    "no_export": bool(ff & PDFConstants.NO_EXPORT_FLAG),
                    "multiline": bool(ff & PDFConstants.MULTILINE_FLAG),
                    "password": bool(ff & PDFConstants.PASSWORD_FLAG),
                    "radio": bool(ff & PDFConstants.RADIO_FLAG),
                    "pushbutton": bool(ff & PDFConstants.PUSHBUTTON_FLAG),
                    "combo": bool(ff & PDFConstants.COMBO_FLAG),
                })
            
            # Extract other properties
            properties.update({
                "tooltip": str(field_obj.get("/TU", "")),  # User name/tooltip
                "mapping_name": str(field_obj.get("/TM", "")),  # Mapping name
                "alternate_name": str(field_obj.get("/T", "")),  # Partial field name
                "max_length": field_obj.get("/MaxLen"),  # Maximum text length
            })
            
            # Extract options for choice fields
            if "/Opt" in field_obj:
                options = field_obj["/Opt"]
                if isinstance(options, (list, ArrayObject)):
                    try:
                        # Handle both direct values and indirect references
                        option_list = []
                        for opt in options:
                            if hasattr(opt, 'get_object'):
                                option_list.append(str(opt.get_object()))
                            else:
                                option_list.append(str(opt))
                        properties["options"] = option_list
                    except Exception as e:
                        logger.warning(f"Error extracting options: {str(e)}")
                        properties["options"] = []
            
            # Extract default appearance
            if "/DA" in field_obj:
                properties["default_appearance"] = str(field_obj["/DA"])
            
        except Exception as e:
            logger.warning(f"Error extracting field properties: {str(e)}")
            properties["extraction_error"] = str(e)
        
        return properties
    
    def _get_field_export_value(self, field_obj: DictionaryObject) -> Optional[str]:
        """
        Extract export value from radio button or checkbox widget.
        
        For radio buttons, this is often the value that gets exported when selected.
        Can be found in /AS (appearance state) or /AP (appearance dictionary).
        """
        try:
            # Try appearance state first
            if "/AS" in field_obj:
                as_value = field_obj["/AS"]
                if as_value and str(as_value) not in ["/Off", "/No"]:
                    return str(as_value).lstrip("/")
            
            # Try appearance dictionary
            if "/AP" in field_obj:
                ap = field_obj["/AP"]
                if isinstance(ap, DictionaryObject) and "/N" in ap:
                    normal_ap = ap["/N"]
                    if isinstance(normal_ap, DictionaryObject):
                        # Get the keys (excluding /Off)
                        keys = [str(k).lstrip("/") for k in normal_ap.keys() 
                               if str(k) not in ["/Off", "/No"]]
                        if keys:
                            return keys[0]  # Take the first non-off state
            
            # Try checking for /V value
            if "/V" in field_obj:
                value = field_obj["/V"]
                if value and str(value) not in ["Off", "No", ""]:
                    return str(value).lstrip("/")
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting export value: {str(e)}")
            return None
    
    def get_field_statistics(self, fields: Optional[List[FormField]] = None) -> Dict[str, Any]:
        """
        Get comprehensive statistics about form fields.
        
        Args:
            fields: List of FormField objects. If None, extracts fields first.
            
        Returns:
            Dictionary containing field statistics
        """
        if fields is None:
            fields = self.extract_form_fields()
        
        stats = {
            "total_fields": len(fields),
            "field_types": {},
            "pages_with_fields": set(),
            "required_fields": 0,
            "readonly_fields": 0,
            "fields_with_values": 0,
            "average_field_size": 0.0,
            "field_distribution": {}
        }
        
        if not fields:
            stats["pages_with_fields"] = 0
            return stats
        
        total_area = 0.0
        
        for field in fields:
            # Count by type
            field_type = field.field_type
            if field_type not in stats["field_types"]:
                stats["field_types"][field_type] = 0
            stats["field_types"][field_type] += 1
            
            # Track pages
            stats["pages_with_fields"].add(field.page)
            
            # Count field properties
            if field.is_required:
                stats["required_fields"] += 1
            
            if field.is_readonly:
                stats["readonly_fields"] += 1
            
            if field.value and str(field.value).strip():
                stats["fields_with_values"] += 1
            
            # Calculate field area
            area = field.width * field.height
            total_area += area
        
        # Convert pages set to count
        stats["pages_with_fields"] = len(stats["pages_with_fields"])
        
        # Calculate average field size
        if len(fields) > 0:
            stats["average_field_size"] = total_area / len(fields)
        
        # Add percentage distributions
        if stats["total_fields"] > 0:
            stats["field_distribution"] = {
                "required_percentage": (stats["required_fields"] / stats["total_fields"]) * 100,
                "readonly_percentage": (stats["readonly_fields"] / stats["total_fields"]) * 100,
                "filled_percentage": (stats["fields_with_values"] / stats["total_fields"]) * 100
            }
        
        return stats
    
    def find_fields_by_type(self, field_type: str, fields: Optional[List[FormField]] = None) -> List[FormField]:
        """
        Find all fields of a specific type.
        
        Args:
            field_type: Type of field to find ('text', 'checkbox', etc.)
            fields: List of FormField objects. If None, extracts fields first.
            
        Returns:
            List of fields matching the specified type
        """
        if fields is None:
            fields = self.extract_form_fields()
        
        return [field for field in fields if field.field_type == field_type]
    
    def find_fields_by_page(self, page_number: int, fields: Optional[List[FormField]] = None) -> List[FormField]:
        """
        Find all fields on a specific page.
        
        Args:
            page_number: Page number (1-based)
            fields: List of FormField objects. If None, extracts fields first.
            
        Returns:
            List of fields on the specified page
        """
        if fields is None:
            fields = self.extract_form_fields()
        
        return [field for field in fields if field.page == page_number]
    
    def clear_cache(self):
        """Clear cached field data to free memory."""
        self._field_cache = None
        logger.debug("Field cache cleared")
    
    def validate_field_structure(self, fields: Optional[List[FormField]] = None) -> Dict[str, Any]:
        """
        Validate the structure and integrity of extracted fields.
        
        Args:
            fields: List of FormField objects. If None, extracts fields first.
            
        Returns:
            Validation report with issues and statistics
        """
        if fields is None:
            fields = self.extract_form_fields()
        
        validation_report = {
            "total_fields": len(fields),
            "valid_fields": 0,
            "issues": [],
            "warnings": [],
            "field_names": [],
            "duplicate_names": []
        }
        
        field_names = []
        
        for field in fields:
            is_valid = True
            
            # Check field name
            if not field.name or field.name.startswith("Field_"):
                validation_report["warnings"].append(f"Field {field.id} has auto-generated name: {field.name}")
            
            # Check field coordinates
            if all(coord == 0.0 for coord in field.rect):
                validation_report["issues"].append(f"Field {field.id} has invalid coordinates: {field.rect}")
                is_valid = False
            
            # Check page number
            if field.page < 1 or field.page > self.pdf_analyzer.get_page_count():
                validation_report["issues"].append(f"Field {field.id} has invalid page number: {field.page}")
                is_valid = False
            
            # Track field names for duplicate detection
            field_names.append(field.name)
            
            if is_valid:
                validation_report["valid_fields"] += 1
        
        # Check for duplicate names
        seen_names = set()
        for name in field_names:
            if name in seen_names:
                validation_report["duplicate_names"].append(name)
            else:
                seen_names.add(name)
        
        validation_report["field_names"] = field_names
        
        return validation_report


@dataclass
class FieldContext:
    """
    Represents contextual information extracted around a form field.
    
    This includes nearby text, labels, section headers, and other contextual
    information that can be used for intelligent field naming.
    """
    
    field_id: str
    nearby_text: List[str] = dataclass_field(default_factory=list)
    section_header: str = ""
    label: str = ""
    confidence: float = 0.0
    visual_group: str = ""
    text_above: str = ""
    text_below: str = ""
    text_left: str = ""
    text_right: str = ""
    context_properties: Dict[str, Any] = dataclass_field(default_factory=dict)


class ContextExtractor:
    """
    Extracts contextual information around form fields for intelligent naming.
    
    This class analyzes PDF page content to identify labels, section headers,
    and other contextual elements that can help generate meaningful field names.
    """
    
    def __init__(self, pdf_analyzer: PDFAnalyzer):
        """
        Initialize the context extractor.
        
        Args:
            pdf_analyzer: PDFAnalyzer instance for accessing PDF content
        """
        self.pdf_analyzer = pdf_analyzer
        self.reader = pdf_analyzer.reader
        self._page_texts = {}  # Cache for extracted page texts
        self._text_elements = {}  # Cache for text elements with positions
        
    def extract_field_context(self, field: FormField) -> FieldContext:
        """
        Extract contextual information for a specific field.
        
        Args:
            field: FormField instance to extract context for
            
        Returns:
            FieldContext instance with extracted contextual information
        """
        try:
            # Get page text if not cached
            page_text = self._get_page_text(field.page)
            
            # Extract text elements with positions (simplified approach)
            text_elements = self._extract_text_elements(field.page)
            
            # Find nearby text based on field coordinates
            nearby_text = self._find_nearby_text(text_elements, field.rect)
            
            # Detect probable field label
            label = self._detect_field_label(nearby_text, field.rect)
            
            # Find section header
            section_header = self._find_section_header(page_text, field.rect)
            
            # Determine visual grouping
            visual_group = self._determine_visual_group(field, text_elements)
            
            # Extract directional text
            text_above = self._extract_directional_text(text_elements, field.rect, "above")
            text_below = self._extract_directional_text(text_elements, field.rect, "below")
            text_left = self._extract_directional_text(text_elements, field.rect, "left")
            text_right = self._extract_directional_text(text_elements, field.rect, "right")
            
            # Calculate confidence score
            confidence = self._calculate_context_confidence(
                label, nearby_text, section_header, text_above, text_left
            )
            
            # Build context properties
            context_properties = {
                "field_type": field.field_type,
                "field_name": field.name,
                "page_number": field.page,
                "coordinates": field.rect,
                "extraction_method": "proximity_analysis"
            }
            
            return FieldContext(
                field_id=field.id,
                nearby_text=nearby_text,
                section_header=section_header,
                label=label,
                confidence=confidence,
                visual_group=visual_group,
                text_above=text_above,
                text_below=text_below,
                text_left=text_left,
                text_right=text_right,
                context_properties=context_properties
            )
            
        except Exception as e:
            logger.error(f"Error extracting context for field {field.id}: {str(e)}")
            return FieldContext(
                field_id=field.id,
                confidence=0.0,
                context_properties={"error": str(e)}
            )
    
    def extract_all_contexts(self, fields: List[FormField]) -> Dict[str, FieldContext]:
        """
        Extract context for all fields in the list.
        
        Args:
            fields: List of FormField instances
            
        Returns:
            Dictionary mapping field IDs to their contexts
        """
        contexts = {}
        
        for field in fields:
            context = self.extract_field_context(field)
            contexts[field.id] = context
            
        return contexts
    
    def clear_cache(self):
        """Clear cached text data to free memory."""
        self._page_texts.clear()
        self._text_elements.clear()
        logger.debug("Context extractor cache cleared")
    
    def _get_page_text(self, page_num: int) -> str:
        """
        Get text content for a specific page (with caching).
        
        Args:
            page_num: Page number (1-based)
            
        Returns:
            Page text content
        """
        if page_num not in self._page_texts:
            try:
                if 1 <= page_num <= len(self.reader.pages):
                    page = self.reader.pages[page_num - 1]
                    self._page_texts[page_num] = page.extract_text()
                else:
                    self._page_texts[page_num] = ""
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                self._page_texts[page_num] = ""
        
        return self._page_texts[page_num]
    
    def _extract_text_elements(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract text elements with approximate positions.
        
        This is a simplified approach using line-based text extraction.
        A more sophisticated implementation would parse the page content stream.
        
        Args:
            page_num: Page number (1-based)
            
        Returns:
            List of text elements with position information
        """
        if page_num not in self._text_elements:
            try:
                page_text = self._get_page_text(page_num)
                elements = []
                
                # Split text into lines and create approximate positions
                lines = page_text.split('\n')
                y_position = PDFConstants.DEFAULT_TOP_MARGIN  # Start from top of page (approximate)
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:
                        # Approximate positioning (real implementation would need content stream parsing)
                        elements.append({
                            'text': line,
                            'x': PDFConstants.DEFAULT_LEFT_MARGIN,  # Approximate left margin
                            'y': y_position,
                            'width': len(line) * PDFConstants.APPROXIMATE_CHAR_WIDTH,  # Approximate width
                            'height': PDFConstants.APPROXIMATE_LINE_HEIGHT,  # Approximate line height
                            'line_index': i
                        })
                        y_position -= PDFConstants.LINE_SPACING  # Move down for next line
                
                self._text_elements[page_num] = elements
                
            except Exception as e:
                logger.warning(f"Error extracting text elements from page {page_num}: {str(e)}")
                self._text_elements[page_num] = []
        
        return self._text_elements[page_num]
    
    def _find_nearby_text(self, text_elements: List[Dict[str, Any]], field_rect: List[float]) -> List[str]:
        """
        Find text elements near the field coordinates.
        
        Args:
            text_elements: List of text elements with positions
            field_rect: Field coordinates [x1, y1, x2, y2]
            
        Returns:
            List of nearby text strings
        """
        if not text_elements or len(field_rect) != 4:
            return []
        
        nearby_text = []
        field_x, field_y = field_rect[0], field_rect[1]
        proximity_threshold = FieldExtractionConstants.PROXIMITY_THRESHOLD
        
        for element in text_elements:
            text = element.get('text', '').strip()
            if not text:
                continue
                
            # Calculate distance from field
            text_x, text_y = element.get('x', 0), element.get('y', 0)
            distance = ((text_x - field_x) ** 2 + (text_y - field_y) ** 2) ** 0.5
            
            if distance <= proximity_threshold:
                nearby_text.append(text)
        
        # Sort by relevance (labels, questions, etc.)
        nearby_text.sort(key=lambda x: (
            0 if ':' in x else 1,  # Prefer text with colons (labels)
            0 if '?' in x else 1,  # Prefer questions
            0 if len(x.split()) <= 5 else 1,  # Prefer short text
            len(x)  # Shorter first
        ))
        
        return nearby_text[:FieldExtractionConstants.MAX_NEARBY_TEXT]  # Limit to most relevant
    
    def _detect_field_label(self, nearby_text: List[str], field_rect: List[float]) -> str:
        """
        Detect the most likely label for the field.
        
        Args:
            nearby_text: List of nearby text strings
            field_rect: Field coordinates
            
        Returns:
            Detected label text
        """
        if not nearby_text:
            return ""
        
        # Look for text that ends with colon (common label pattern)
        for text in nearby_text:
            if text.strip().endswith(':'):
                return text.strip().rstrip(':')
        
        # Look for text that contains common field indicators
        field_indicators = ['name', 'address', 'phone', 'email', 'date', 'amount', 'signature']
        for text in nearby_text:
            text_lower = text.lower()
            for indicator in field_indicators:
                if indicator in text_lower:
                    return text.strip()
        
        # Fall back to first nearby text if it's reasonably short
        first_text = nearby_text[0].strip()
        if len(first_text.split()) <= 5:
            return first_text
        
        return ""
    
    def _find_section_header(self, page_text: str, field_rect: List[float]) -> str:
        """
        Find the section header for this field.
        
        Args:
            page_text: Full page text content
            field_rect: Field coordinates
            
        Returns:
            Section header text
        """
        if not page_text:
            return ""
        
        lines = page_text.split('\n')
        
        # Look for lines that might be section headers
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Common section header patterns
            if (line.isupper() or 
                'section' in line.lower() or 
                'part' in line.lower() or
                'information' in line.lower() or
                line.endswith(':') and len(line.split()) <= 4):
                return line.rstrip(':')
        
        return ""
    
    def _determine_visual_group(self, field: FormField, text_elements: List[Dict[str, Any]]) -> str:
        """
        Determine visual grouping for the field based on layout.
        
        Args:
            field: FormField instance
            text_elements: Text elements for context
            
        Returns:
            Visual group identifier
        """
        if len(field.rect) != 4:
            return "unknown"
        
        # Simple grouping based on vertical position
        field_y = field.rect[1]
        
        if field_y > PDFConstants.HEADER_SECTION_THRESHOLD:
            return "header_section"
        elif field_y > PDFConstants.UPPER_SECTION_THRESHOLD:
            return "upper_section"
        elif field_y > PDFConstants.MIDDLE_SECTION_THRESHOLD:
            return "middle_section"
        elif field_y > PDFConstants.LOWER_SECTION_THRESHOLD:
            return "lower_section"
        else:
            return "footer_section"
    
    def _extract_directional_text(self, text_elements: List[Dict[str, Any]], 
                                 field_rect: List[float], direction: str) -> str:
        """
        Extract text in a specific direction from the field.
        
        Args:
            text_elements: Text elements with positions
            field_rect: Field coordinates
            direction: Direction to look ('above', 'below', 'left', 'right')
            
        Returns:
            Text found in the specified direction
        """
        if not text_elements or len(field_rect) != 4:
            return ""
        
        field_x, field_y = field_rect[0], field_rect[1]
        field_width, field_height = field_rect[2] - field_rect[0], field_rect[3] - field_rect[1]
        
        candidates = []
        
        for element in text_elements:
            text = element.get('text', '').strip()
            if not text:
                continue
                
            text_x, text_y = element.get('x', 0), element.get('y', 0)
            
            # Check if text is in the specified direction
            if direction == 'above' and text_y > field_y + field_height:
                candidates.append((text, abs(text_y - (field_y + field_height))))
            elif direction == 'below' and text_y < field_y:
                candidates.append((text, abs(field_y - text_y)))
            elif direction == 'left' and text_x < field_x:
                candidates.append((text, abs(field_x - text_x)))
            elif direction == 'right' and text_x > field_x + field_width:
                candidates.append((text, abs(text_x - (field_x + field_width))))
        
        # Return closest text in the specified direction
        if candidates:
            candidates.sort(key=lambda x: x[1])  # Sort by distance
            return candidates[0][0]
        
        return ""
    
    def _calculate_context_confidence(self, label: str, nearby_text: List[str], 
                                    section_header: str, text_above: str, 
                                    text_left: str) -> float:
        """
        Calculate confidence score for context extraction.
        
        Args:
            label: Detected field label
            nearby_text: List of nearby text
            section_header: Section header
            text_above: Text above the field
            text_left: Text to the left of the field
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = FieldExtractionConstants.CONTEXT_CONFIDENCE_BASE  # Base confidence
        
        # Boost confidence for clear label
        if label:
            if ':' in label or any(word in label.lower() for word in ['name', 'address', 'email', 'phone']):
                confidence += FieldExtractionConstants.LABEL_CONFIDENCE_BOOST
            else:
                confidence += 0.1
        
        # Boost for substantial nearby text
        if len(nearby_text) >= 3:
            confidence += FieldExtractionConstants.NEARBY_TEXT_CONFIDENCE_BOOST
        elif len(nearby_text) >= 1:
            confidence += 0.1
        
        # Boost for section header
        if section_header:
            confidence += FieldExtractionConstants.SECTION_HEADER_CONFIDENCE_BOOST
        
        # Boost for directional text
        if text_above or text_left:
            confidence += FieldExtractionConstants.DIRECTIONAL_TEXT_CONFIDENCE_BOOST
        
        return min(confidence, 1.0)