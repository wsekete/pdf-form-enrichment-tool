# PDF Form Field Editor - Comprehensive Task List

## 📊 Project Progress Overview

**Phase 1: Foundation & Core Parsing**
- ✅ Task 1.1: Project Setup & Environment (COMPLETED)
- ✅ Task 1.2: Basic PDF Reading & Structure Analysis (COMPLETED)  
- 🚧 Task 1.3: Form Field Discovery & Basic Extraction (READY TO START)
- ⏳ Task 1.4: Field Context Extraction (PENDING)

**Overall Status**: 2/4 Foundation tasks complete (50%) - Ready for Task 1.3!

## Development Philosophy

This task list is designed for iterative development using Claude Code, with each phase building upon the previous while maintaining functionality throughout. Each task includes:
- **Clear deliverables** with specific acceptance criteria
- **Incremental complexity** that builds naturally
- **Validation steps** to ensure quality at each stage
- **Rollback safety** to prevent breaking existing functionality

## Phase 1: Foundation & Core Parsing (Week 1)

### Task 1.1: Project Setup & Environment ✅
**Status**: COMPLETED! You already have this set up.

### Task 1.2: Basic PDF Reading & Structure Analysis ✅
**Status**: COMPLETED! Production-ready PDFAnalyzer with comprehensive testing.  
**Objective**: Implement core PDF parsing capabilities  
**Complexity**: Medium  
**Duration**: 4-6 hours → **Actual: 6 hours (including tests & code review fixes)**

**Deliverables**:
- [x] Install and configure PyPDF library
- [x] Create PDFAnalyzer class with basic file reading
- [x] Implement PDF structure validation (header, xref, trailer)
- [x] Extract basic document metadata (page count, version, encryption status)
- [x] Create error handling for corrupted or invalid PDFs
- [x] Add support for password-protected PDFs
- [x] Implement basic PDF information export to JSON
- [x] **BONUS**: Comprehensive unit tests (31 tests, 78% coverage)
- [x] **BONUS**: CLI integration with analyze and process commands
- [x] **BONUS**: Code review fixes and optimizations

**Acceptance Criteria**: ✅ ALL COMPLETED
- ✅ Successfully opens and reads various PDF formats
- ✅ Handles encrypted PDFs with password prompt
- ✅ Gracefully fails on corrupted files with helpful error messages
- ✅ Exports basic metadata in structured format

**Implementation Summary**:
- **File**: `pdf_form_editor/core/pdf_analyzer.py` (390+ lines)
- **Tests**: `tests/unit/test_pdf_analyzer.py` (31 tests, 100% pass rate)
- **CLI**: Enhanced `analyze` and `process` commands
- **Features**: Metadata caching, comprehensive logging, robust error handling
- **Code Quality**: All code review issues resolved (A- grade → A grade)

**Usage Examples**:
```bash
# CLI Usage
python -m pdf_form_editor analyze sample.pdf
python -m pdf_form_editor process form.pdf --review --output results/

# Python Usage  
from pdf_form_editor.core.pdf_analyzer import PDFAnalyzer
analyzer = PDFAnalyzer("sample.pdf")
metadata = analyzer.extract_metadata()
analyzer.export_metadata_json("analysis.json")
```

**Validation**: ✅ ALL COMPLETED
- ✅ Tested with 5+ different PDF files (system PDFs, form PDFs, various formats)
- ✅ JSON output structure validated and working
- ✅ Error messages are user-friendly and descriptive
- ✅ Comprehensive unit test coverage (31 tests)

---

### Task 1.3: Form Field Discovery & Basic Extraction 🚧
**Status**: READY TO START - Dependencies completed (Task 1.2 ✅)  
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

## 🎯 Next Steps - Ready for Task 1.3!

**Task 1.2 Complete ✅ - Now ready for Task 1.3:**

1. **Foundation is solid**: PDFAnalyzer working with 31 unit tests
2. **Form field extraction**: Next step is to extract actual form fields
3. **Field data structures**: Create FormField classes and extraction logic
4. **Test with real forms**: Use PDFs with actual form fields
5. **Ask Claude Code for help** with Task 1.3 implementation

## 💡 Development Tips

- **Build on the PDFAnalyzer**: Use existing validation and error handling
- **Test with form PDFs**: Focus on PDFs that actually have form fields
- **Use the W-4R test PDF**: Known to have 10 form fields for testing
- **Read PyPDF documentation**: [pypdf.readthedocs.io](https://pypdf.readthedocs.io/)
- **Follow the task structure**: Each task builds on the previous

## 🆘 When You Get Stuck

1. **Use existing PDFAnalyzer**: Leverage the solid foundation already built
2. **Test form detection**: Verify `has_form_fields()` returns True first
3. **Start simple**: Extract basic field names before complex properties
4. **Ask Claude Code** for specific field extraction help
5. **Check the W-4R PDF**: Known working test case with form fields

**Task 1.2 foundation complete - let's extract those form fields! 🚀**
