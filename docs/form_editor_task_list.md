# PDF Form Field Editor - Comprehensive Task List

## Development Philosophy

This task list is designed for iterative development using Claude Code, with each phase building upon the previous while maintaining functionality throughout. Each task includes:
- **Clear deliverables** with specific acceptance criteria
- **Incremental complexity** that builds naturally
- **Validation steps** to ensure quality at each stage
- **Rollback safety** to prevent breaking existing functionality

## Phase 1: Foundation & Core Parsing (Week 1)

### Task 1.1: Project Setup & Environment ✅
**Status**: COMPLETED! You already have this set up.

### Task 1.2: Basic PDF Reading & Structure Analysis
**Objective**: Implement core PDF parsing capabilities  
**Complexity**: Medium  
**Duration**: 4-6 hours

**Deliverables**:
- [ ] Install and configure PyPDF library
- [ ] Create PDFAnalyzer class with basic file reading
- [ ] Implement PDF structure validation (header, xref, trailer)
- [ ] Extract basic document metadata (page count, version, encryption status)
- [ ] Create error handling for corrupted or invalid PDFs
- [ ] Add support for password-protected PDFs
- [ ] Implement basic PDF information export to JSON

**Acceptance Criteria**:
- Successfully opens and reads various PDF formats
- Handles encrypted PDFs with password prompt
- Gracefully fails on corrupted files with helpful error messages
- Exports basic metadata in structured format

**Code Structure**:
```python
# Create: pdf_form_editor/core/pdf_analyzer.py
from pypdf import PdfReader
from typing import Optional, Dict, Any
import json
from pathlib import Path

class PDFAnalyzer:
    def __init__(self, file_path: str, password: str = None):
        self.file_path = Path(file_path)
        self.password = password
        self.reader = None
        self._load_pdf()
    
    def _load_pdf(self):
        """Load PDF with error handling."""
        try:
            self.reader = PdfReader(str(self.file_path))
            if self.reader.is_encrypted:
                if self.password:
                    self.reader.decrypt(self.password)
                else:
                    raise ValueError("PDF is encrypted but no password provided")
        except Exception as e:
            raise ValueError(f"Could not load PDF: {e}")
    
    def validate_pdf(self) -> bool:
        """Check if file is a valid PDF."""
        return self.reader is not None and len(self.reader.pages) > 0
    
    def extract_metadata(self) -> dict:
        """Extract basic PDF metadata."""
        if not self.reader:
            return {}
        
        metadata = {
            "file_path": str(self.file_path),
            "page_count": len(self.reader.pages),
            "is_encrypted": self.reader.is_encrypted,
            "has_form_fields": self.has_form_fields(),
            "pdf_version": getattr(self.reader, 'pdf_header', 'Unknown')
        }
        
        if self.reader.metadata:
            metadata.update({
                "title": self.reader.metadata.get('/Title'),
                "author": self.reader.metadata.get('/Author'),
                "creator": self.reader.metadata.get('/Creator'),
                "creation_date": str(self.reader.metadata.get('/CreationDate', '')),
                "modification_date": str(self.reader.metadata.get('/ModDate', ''))
            })
        
        return metadata
    
    def get_page_count(self) -> int:
        """Get number of pages in PDF."""
        return len(self.reader.pages) if self.reader else 0
    
    def has_form_fields(self) -> bool:
        """Check if PDF contains form fields."""
        if not self.reader:
            return False
        
        # Check for AcroForm
        catalog = self.reader.trailer.get("/Root")
        return bool(catalog and "/AcroForm" in catalog)
    
    def is_encrypted(self) -> bool:
        """Check if PDF is encrypted."""
        return self.reader.is_encrypted if self.reader else False
    
    def get_pdf_version(self) -> str:
        """Get PDF version."""
        return getattr(self.reader, 'pdf_header', 'Unknown') if self.reader else 'Unknown'
    
    def export_metadata_json(self, output_path: str) -> None:
        """Export metadata to JSON file."""
        metadata = self.extract_metadata()
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
```

**Validation**:
- Test with 5+ different PDF files (simple, complex, encrypted, corrupted)
- Verify JSON output structure matches expected schema
- Confirm error messages are user-friendly

---

### Task 1.3: Form Field Discovery & Basic Extraction
**Objective**: Locate and extract form fields from PDF  
**Complexity**: Medium-High  
**Duration**: 6-8 hours

**Deliverables**:
- [ ] Implement AcroForm dictionary detection and parsing
- [ ] Create FormField data class with essential properties
- [ ] Extract basic field information (name, type, page, coordinates)
- [ ] Handle different field types (text, checkbox, radio, dropdown, signature)
- [ ] Implement field enumeration with proper indexing
- [ ] Create field validation and type checking
- [ ] Add field count and type statistics

**Acceptance Criteria**:
- Correctly identifies all form fields in test PDFs
- Properly categorizes field types
- Extracts accurate coordinate information
- Provides comprehensive field inventory

**Data Structure**:
```python
# Create: pdf_form_editor/core/field_extractor.py
from dataclasses import dataclass
from typing import List, Any, Dict, Optional
from pypdf import PdfReader
from pypdf.generic import DictionaryObject

@dataclass
class FormField:
    id: str
    name: str
    field_type: str  # 'text', 'checkbox', 'radio', 'choice', 'signature'
    page: int
    rect: List[float]  # [x1, y1, x2, y2]
    value: Any
    properties: Dict[str, Any]
    parent: Optional[str] = None
    children: List[str] = None

class FieldExtractor:
    def __init__(self, pdf_analyzer):
        self.pdf_analyzer = pdf_analyzer
        self.reader = pdf_analyzer.reader
    
    def extract_form_fields(self) -> List[FormField]:
        """Extract all form fields from PDF."""
        if not self.reader or not self.pdf_analyzer.has_form_fields():
            return []
        
        fields = []
        form = self.reader.trailer["/Root"]["/AcroForm"]
        
        if "/Fields" in form:
            for i, field_ref in enumerate(form["/Fields"]):
                field_obj = field_ref.get_object()
                field = self._parse_field(field_obj, i)
                if field:
                    fields.append(field)
        
        return fields
    
    def _parse_field(self, field_obj: DictionaryObject, index: int) -> Optional[FormField]:
        """Parse individual field object."""
        try:
            # Get field properties
            field_name = field_obj.get("/T", f"Field_{index}")
            field_type = self._determine_field_type(field_obj)
            field_value = field_obj.get("/V", "")
            field_rect = field_obj.get("/Rect", [0, 0, 0, 0])
            
            # Find which page this field is on
            page_num = self._find_field_page(field_obj)
            
            # Extract additional properties
            properties = {
                "required": "/Ff" in field_obj and bool(field_obj["/Ff"] & 2),
                "readonly": "/Ff" in field_obj and bool(field_obj["/Ff"] & 1),
                "multiline": "/Ff" in field_obj and bool(field_obj["/Ff"] & 4096),
                "password": "/Ff" in field_obj and bool(field_obj["/Ff"] & 8192),
            }
            
            return FormField(
                id=f"field_{index:03d}",
                name=str(field_name),
                field_type=field_type,
                page=page_num,
                rect=[float(x) for x in field_rect],
                value=field_value,
                properties=properties
            )
            
        except Exception as e:
            print(f"Error parsing field {index}: {e}")
            return None
    
    def _determine_field_type(self, field_obj: DictionaryObject) -> str:
        """Determine the type of form field."""
        ft = field_obj.get("/FT", "")
        
        if ft == "/Tx":
            return "text"
        elif ft == "/Btn":
            # Check if it's radio or checkbox
            if "/Ff" in field_obj and bool(field_obj["/Ff"] & 32768):
                return "radio"
            else:
                return "checkbox"
        elif ft == "/Ch":
            return "choice"  # dropdown or listbox
        elif ft == "/Sig":
            return "signature"
        else:
            return "unknown"
    
    def _find_field_page(self, field_obj: DictionaryObject) -> int:
        """Find which page contains this field."""
        # This is simplified - in practice you'd need to traverse the page tree
        # For now, return page 1 as default
        return 1
    
    def get_field_statistics(self, fields: List[FormField]) -> Dict[str, Any]:
        """Get statistics about form fields."""
        stats = {
            "total_fields": len(fields),
            "field_types": {},
            "pages_with_fields": set(),
            "required_fields": 0
        }
        
        for field in fields:
            # Count by type
            if field.field_type not in stats["field_types"]:
                stats["field_types"][field.field_type] = 0
            stats["field_types"][field.field_type] += 1
            
            # Track pages
            stats["pages_with_fields"].add(field.page)
            
            # Count required fields
            if field.properties.get("required", False):
                stats["required_fields"] += 1
        
        stats["pages_with_fields"] = len(stats["pages_with_fields"])
        return stats
```

**Validation**:
- Test with forms containing 10+, 50+, and 100+ fields
- Verify field coordinates map correctly to visual layout
- Confirm all field types are properly detected

---

### Task 1.4: Field Context Extraction
**Objective**: Extract contextual information around form fields  
**Complexity**: High  
**Duration**: 8-10 hours

**Deliverables**:
- [ ] Implement text extraction around field coordinates
- [ ] Create proximity-based label detection algorithm
- [ ] Extract section headers and form structure
- [ ] Identify field groupings based on visual layout
- [ ] Create context confidence scoring system
- [ ] Generate field context reports

**Acceptance Criteria**:
- Accurately identifies field labels and nearby text
- Detects form sections and groupings
- Provides confidence scores for context extraction
- Handles complex multi-column layouts

**Context Structure**:
```python
# Add to: pdf_form_editor/core/field_extractor.py
@dataclass
class FieldContext:
    field_id: str
    nearby_text: List[str]
    section_header: str
    label: str
    confidence: float
    visual_group: str
    text_above: str = ""
    text_below: str = ""
    text_left: str = ""
    text_right: str = ""

class ContextExtractor:
    def __init__(self, pdf_analyzer):
        self.pdf_analyzer = pdf_analyzer
        self.reader = pdf_analyzer.reader
    
    def extract_field_context(self, field: FormField) -> FieldContext:
        """Extract context for a specific field."""
        # Get the page containing this field
        page = self.reader.pages[field.page - 1]
        
        # Extract text from the page
        page_text = page.extract_text()
        
        # Find text near the field coordinates
        nearby_text = self._find_nearby_text(page, field.rect)
        
        # Detect probable label
        label = self._detect_field_label(nearby_text, field.rect)
        
        # Find section header
        section_header = self._find_section_header(page_text, field.rect)
        
        # Calculate confidence
        confidence = self._calculate_context_confidence(label, nearby_text)
        
        return FieldContext(
            field_id=field.id,
            nearby_text=nearby_text,
            section_header=section_header,
            label=label,
            confidence=confidence,
            visual_group=self._determine_visual_group(field)
        )
    
    def _find_nearby_text(self, page, field_rect: List[float]) -> List[str]:
        """Find text elements near the field."""
        # This is a simplified implementation
        # In practice, you'd need to parse the page content stream
        # to get precise text positioning
        
        nearby_text = []
        page_text = page.extract_text()
        
        # Split into lines and filter for relevant text
        lines = page_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 1:
                # Simple heuristic: text that looks like labels
                if ':' in line or line.endswith('?') or len(line.split()) <= 5:
                    nearby_text.append(line)
        
        return nearby_text[:10]  # Limit to 10 nearest items
    
    def _detect_field_label(self, nearby_text: List[str], field_rect: List[float]) -> str:
        """Detect the most likely label for this field."""
        if not nearby_text:
            return ""
        
        # Look for text that ends with colon (common label pattern)
        for text in nearby_text:
            if text.strip().endswith(':'):
                return text.strip().rstrip(':')
        
        # Fall back to first nearby text
        return nearby_text[0].strip()
    
    def _find_section_header(self, page_text: str, field_rect: List[float]) -> str:
        """Find the section header for this field."""
        lines = page_text.split('\n')
        
        # Look for lines that might be section headers
        # (typically all caps, or followed by multiple fields)
        for line in lines:
            line = line.strip()
            if line and (line.isupper() or 'information' in line.lower() or 'section' in line.lower()):
                return line
        
        return ""
    
    def _calculate_context_confidence(self, label: str, nearby_text: List[str]) -> float:
        """Calculate confidence score for context extraction."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence if we found a clear label
        if label and ':' in label:
            confidence += 0.3
        
        # Boost if we have substantial nearby text
        if len(nearby_text) >= 3:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _determine_visual_group(self, field: FormField) -> str:
        """Determine visual grouping for the field."""
        # Simplified grouping based on field position
        x, y = field.rect[0], field.rect[1]
        
        if y > 600:
            return "top_section"
        elif y > 400:
            return "middle_section"
        else:
            return "bottom_section"
```

**Validation**:
- Test with forms having clear labels vs. complex layouts
- Verify context extraction accuracy ≥80%
- Confirm section detection works for multi-page forms

---

## Phase 2: BEM Name Generation & AI Integration (Week 2)

### Task 2.1: BEM Naming Rules Engine
**Objective**: Implement core BEM naming logic and validation  
**Complexity**: Medium  
**Duration**: 4-6 hours

**Deliverables**:
- [ ] Create BEMNamingEngine class with rule validation
- [ ] Implement block, element, modifier pattern recognition
- [ ] Create naming convention validation and compliance checking
- [ ] Add special case handling (radio groups, signatures, custom fields)
- [ ] Implement name uniqueness checking within document scope
- [ ] Create BEM pattern templates and examples
- [ ] Add name generation confidence scoring

**Getting Started Right Now:**

```bash
# Create the core directory if it doesn't exist
mkdir -p pdf_form_editor/core

# Create empty __init__.py files
touch pdf_form_editor/core/__init__.py

# Start with Task 1.2 - create the PDF analyzer
touch pdf_form_editor/core/pdf_analyzer.py
```

**Then copy the PDFAnalyzer code above into the file and test it!**

## 🎯 Start Building Today

**Pick Task 1.2 and begin:**

1. **Create the file**: `pdf_form_editor/core/pdf_analyzer.py`
2. **Copy the code structure** from above
3. **Test with a sample PDF**
4. **Ask Claude Code for help** with any issues
5. **Move to Task 1.3** when working

## 💡 Development Tips

- **Start with simple PDFs** before trying complex ones
- **Test each piece** before moving to the next
- **Use print statements** to debug what's happening
- **Ask Claude Code** for help implementing specific parts
- **Read PyPDF documentation**: [pypdf.readthedocs.io](https://pypdf.readthedocs.io/)

## 🆘 When You Get Stuck

1. **Check the error message** carefully
2. **Verify your PDF file** exists and is valid
3. **Test with a different PDF** to isolate the issue
4. **Ask Claude Code** for specific implementation help
5. **Use the debugging commands** in the code structure

**Start with Task 1.2 and let's build your PDF processing superpower! 🚀**
