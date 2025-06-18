#!/usr/bin/env python3
"""
Add Comprehensive Documentation to PDF Form Enrichment Tool

This script adds all the detailed documentation files including task lists,
PRDs, and guides.
"""

import os
from pathlib import Path

def create_file_with_content(filepath, content):
    """Create a file with the given content."""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {filepath}")
    except Exception as e:
        print(f"❌ Error creating {filepath}: {e}")

def add_comprehensive_documentation():
    """Add all comprehensive documentation files."""
    
    # Create docs directory
    Path("docs").mkdir(exist_ok=True)
    
    # Complete Task List
    task_list_content = '''# PDF Form Field Editor - Comprehensive Task List

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
        lines = page_text.split('\\n')
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
        lines = page_text.split('\\n')
        
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
'''

    # Product Requirements Document
    prd_content = '''# PDF Form Field Editor - Product Requirements Document

## Executive Summary

The PDF Form Field Editor is a Python-based tool that automatically parses PDF forms, extracts form field metadata, generates BEM-compliant API names using AI-powered contextual analysis, and writes changes back to the PDF while preserving document integrity. This tool addresses the critical bottleneck in our forms processing pipeline by automating the manual, time-consuming field renaming process.

## Problem Statement

### Current State
- Manual PDF form field renaming is time-intensive and error-prone
- Process requires Adobe Acrobat expertise  
- Major scalability bottleneck for company growth
- Inconsistent naming conventions across forms
- Risk of PDF corruption during manual editing

### Business Impact
- **Time**: 2-4 hours per form → Target: 5-10 minutes
- **Accuracy**: 85-90% consistency → Target: 98%+ consistency
- **Scalability**: Current team can process ~20 forms/week → Target: 100+ forms/week
- **Quality**: Reduces downstream API integration issues

## Solution Overview

### Core Functionality
1. **PDF Form Analysis**: Extract form field metadata and contextual information
2. **AI-Powered Naming**: Generate BEM-compliant names using field context and training data
3. **Safe PDF Modification**: Update field properties while preserving document structure
4. **Validation & Review**: Comprehensive validation and human review interface
5. **Export & Integration**: Output modified PDFs with metadata for downstream systems

### Technology Stack
- **Primary**: Python 3.9+ with PyPDF library
- **AI Integration**: OpenAI API for contextual name generation
- **Validation**: Adobe PDF Services API (Get PDF Properties)
- **Data**: JSON for metadata handling
- **Interface**: CLI with optional web interface

## BEM Naming Convention

This tool follows the BEM (Block Element Modifier) naming convention:

```
block_element__modifier
```

- **Block**: Form sections (e.g., `owner-information`, `payment`)
- **Element**: Individual fields (e.g., `name`, `email`, `phone-number`)  
- **Modifier**: Field variations (e.g., `first`, `last`, `primary`)

### Examples

- `owner-information_name`
- `owner-information_name__first`
- `payment_amount__gross`
- `signatures_owner`

## Success Metrics

### Primary KPIs
- **Processing Time**: 90% reduction from manual process
- **Accuracy Rate**: 95%+ BEM naming compliance
- **Error Rate**: <2% PDF corruption or functionality loss
- **User Adoption**: 100% of forms team using tool within 30 days

### Secondary Metrics
- **Throughput**: 10x increase in forms processed per week
- **Consistency**: 98% adherence to naming conventions
- **User Satisfaction**: 9/10 ease-of-use rating
- **Support Tickets**: <5% related to field naming issues

## Implementation Phases

### Phase 1: Core MVP (Weeks 1-2)
- Basic PDF parsing and field extraction
- Simple BEM name generation
- CLI interface for single PDF processing

### Phase 2: Enhanced Features (Weeks 3-4)
- AI-powered contextual naming
- Review interface with approval workflow
- Batch processing capability

### Phase 3: Production Ready (Weeks 5-6)
- Comprehensive error handling
- Performance optimization
- Integration with Adobe API validation

### Phase 4: Advanced Features (Future)
- Web interface
- Plugin architecture
- Advanced analytics and reporting

This tool will transform your forms processing workflow from a manual bottleneck into an automated superpower! 🚀
'''

    # MCP Server PRD (condensed)
    mcp_prd_content = '''# MCP Server for PDF Form Editor - Product Requirements Document

## Executive Summary

The MCP (Model Context Protocol) Server for PDF Form Editor enables seamless integration of the PDF Form Field Editor with Claude Desktop, providing an intuitive conversational interface for form processing workflows.

## Solution Overview

### Core Functionality
1. **MCP Integration**: Full compatibility with Claude Desktop's MCP framework
2. **Conversational Interface**: Natural language commands for PDF processing
3. **File Management**: Seamless PDF upload and download within Claude Desktop
4. **Review Workflow**: Interactive review and approval of field changes
5. **Progress Tracking**: Real-time status updates and progress reporting

### User Experience Flow
```
User uploads PDF → Claude analyzes form → AI suggests field names → 
User reviews/refines → Changes applied → Download processed PDF
```

## Claude Desktop Integration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "pdf-form-editor": {
      "command": "python",
      "args": ["-m", "pdf_form_editor.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "ADOBE_API_KEY": "${ADOBE_API_KEY}"
      }
    }
  }
}
```

## Development Phases

### Phase 1: Basic MCP Integration (Week 1)
- MCP protocol implementation
- Basic tool registration
- Simple PDF upload/download

### Phase 2: Core Functionality (Week 2)
- Integration with PDF Form Field Editor
- Basic conversational interface
- Progress tracking and status updates

### Phase 3: Enhanced User Experience (Week 3)
- Interactive review workflow
- Advanced conversation handling
- Error recovery and guidance

### Phase 4: Production Polish (Week 4)
- Performance optimization
- Comprehensive testing
- Documentation and deployment

This MCP server will transform the command-line tool into an intuitive, conversational experience within Claude Desktop! 🚀
'''

    # API Reference
    api_reference_content = '''# PDF Form Enrichment Tool - API Reference

## Core Classes

### PDFAnalyzer
```python
from pdf_form_editor.core.pdf_analyzer import PDFAnalyzer

# Create analyzer
analyzer = PDFAnalyzer("path/to/form.pdf", password="optional")

# Basic operations
is_valid = analyzer.validate_pdf()
page_count = analyzer.get_page_count()
has_forms = analyzer.has_form_fields()
metadata = analyzer.extract_metadata()
```

### FormField
```python
from pdf_form_editor.core.field_extractor import FormField

@dataclass
class FormField:
    id: str
    name: str
    field_type: str  # 'text', 'checkbox', 'radio', 'choice', 'signature'
    page: int
    rect: List[float]  # [x1, y1, x2, y2]
    value: Any
    properties: Dict[str, Any]
```

### FieldExtractor
```python
from pdf_form_editor.core.field_extractor import FieldExtractor

# Extract form fields
extractor = FieldExtractor(pdf_analyzer)
fields = extractor.extract_form_fields()
stats = extractor.get_field_statistics(fields)
```

### BEMNameGenerator
```python
from pdf_form_editor.core.bem_generator import BEMNameGenerator

# Generate BEM names
generator = BEMNameGenerator()
bem_name = generator.generate_bem_name(field, context)
is_valid = generator.validate_bem_name(bem_name)
```

## CLI Commands

```bash
# Analyze PDF structure
pdf-form-editor analyze input.pdf

# Process a PDF with review
pdf-form-editor process input.pdf --review

# Batch processing
pdf-form-editor batch *.pdf --output processed/

# Show system info
pdf-form-editor info

# Get help
pdf-form-editor --help
```

## Configuration

Configuration is loaded from:
1. `config/default.yaml` (default settings)
2. Environment variables (override defaults)
3. Command line options (override everything)

Key configuration sections:
- `general`: Basic app settings
- `processing`: PDF processing options
- `ai`: OpenAI API configuration
- `naming`: BEM naming rules
- `mcp_server`: Claude Desktop integration

## Error Handling

All operations use structured exception handling:

```python
from pdf_form_editor.utils.errors import (
    PDFProcessingError,
    ValidationError,
    BEMNamingError,
    AIServiceError,
    ConfigurationError
)

try:
    analyzer = PDFAnalyzer("form.pdf")
    fields = analyzer.extract_form_fields()
except PDFProcessingError as e:
    print(f"PDF processing failed: {e}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## BEM Naming Convention

### Pattern
```
block_element__modifier
```

### Validation Rules
- Lowercase letters, numbers, hyphens only
- Single underscore between block and element
- Double underscore before modifier
- Maximum 100 characters
- No reserved words (group, custom, temp, test)

### Examples
```python
# Valid BEM names
"owner-information_name"
"owner-information_name__first"
"payment_amount__gross"
"signatures_owner"

# Invalid BEM names
"Owner_Name"        # uppercase
"owner_"            # trailing underscore
"_name"             # leading underscore
"owner__name"       # double underscore in wrong place
```

This API provides everything you need to build powerful PDF form processing applications! 🚀
'''

    # User Guide
    user_guide_content = '''# PDF Form Enrichment Tool - User Guide

## Quick Start

### 1. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-form-enrichment-tool.git
cd pdf-form-enrichment-tool

# Set up environment
make setup
source venv/bin/activate  # Mac/Linux
# or: venv\\Scripts\\activate  # Windows

# Install dependencies
make install

# Configure API keys
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 2. Basic Usage

#### Analyze a PDF Form
```bash
python -m pdf_form_editor analyze your_form.pdf
```

This shows you:
- Number of form fields found
- Field types (text, checkbox, radio, etc.)
- Basic PDF information
- Whether the PDF has interactive form fields

#### Process a PDF Form
```bash
python -m pdf_form_editor process your_form.pdf --review
```

This will:
1. Extract all form fields from the PDF
2. Analyze field context using AI
3. Generate BEM-compliant field names
4. Show you a review of proposed changes
5. Let you approve, reject, or modify suggestions
6. Create a new PDF with updated field names

### 3. Understanding the Output

After processing, you'll get:
- **Original PDF**: `your_form.pdf` (unchanged)
- **Processed PDF**: `your_form_parsed.pdf` (with BEM field names)
- **Metadata**: `your_form_metadata.json` (processing details)

## Step-by-Step Workflow

### Step 1: Prepare Your PDF
- Ensure your PDF has interactive form fields
- If it doesn't, you'll need to add them in Adobe Acrobat first
- Place the PDF in your project directory or note the full path

### Step 2: Analyze the Form Structure
```bash
python -m pdf_form_editor analyze your_form.pdf
```

Example output:
```
📄 PDF Analysis: your_form.pdf
   Pages: 3
   Version: %PDF-1.4
   Encrypted: False
   Has forms: True

🔧 Form Fields (23):
   text: 15 fields
   checkbox: 5 fields
   radio: 3 fields

📝 Sample Fields:
   1. TextField1 (text)
   2. TextField2 (text)
   3. CheckBox1 (checkbox)
   4. RadioButton1 (radio)
   5. TextField3 (text)
   ... and 18 more
```

### Step 3: Process with BEM Naming
```bash
python -m pdf_form_editor process your_form.pdf --review
```

The AI will analyze each field and suggest BEM names:

```
🚀 Processing PDF: your_form.pdf
📋 Found 23 form fields

🤖 AI Analysis Complete - Generating BEM names...

📊 Review Results:
┌─────────────────────────────────────────────────────────────┐
│ Field 1/23                            Confidence: 95%       │
│ Original: TextField1                                        │
│ Suggested: owner-information_name__first                    │
│ Context: Found near "Owner Information" and "First Name"   │
│ Actions: [A]pprove [R]eject [M]odify [S]kip [Q]uit        │
└─────────────────────────────────────────────────────────────┘
```

### Step 4: Review and Approve Changes

You can:
- **[A]pprove**: Accept the suggested name
- **[R]eject**: Keep the original name  
- **[M]odify**: Enter a custom BEM name
- **[S]kip**: Skip this field for now
- **[Q]uit**: Exit the review process

#### Bulk Operations
- **"approve all high confidence"**: Approve all suggestions with >90% confidence
- **"reject all low confidence"**: Reject all suggestions with <70% confidence
- **"show only text fields"**: Filter to show only text fields

### Step 5: Get Your Results

After completing the review:
```
✅ Processing completed successfully!
📄 Input: your_form.pdf
📄 Output: your_form_parsed.pdf
🔧 Fields processed: 23
✏️  Fields modified: 18
⏱️  Processing time: 45.2s
🎯 Average confidence: 87%

⚠️  Warnings (2):
   • Field 'TextField15' had low confidence (65%)
   • Field 'RadioButton3' used fallback naming

📊 Metadata exported: your_form_metadata.json
```

## BEM Naming Examples

### Owner Information Section
**Before:**
- `TextField1` → **After:** `owner-information_name__first`
- `TextField2` → **After:** `owner-information_name__last` 
- `TextField3` → **After:** `owner-information_email`
- `TextField4` → **After:** `owner-information_phone`

### Payment Section
**Before:**
- `Amount1` → **After:** `payment_amount__gross`
- `Amount2` → **After:** `payment_amount__net`
- `CheckBox1` → **After:** `payment_consent`
- `TextField10` → **After:** `payment_account-number`

### Signatures Section
**Before:**
- `Signature1` → **After:** `signatures_owner`
- `Date1` → **After:** `signatures_date__owner`
- `Signature2` → **After:** `signatures_witness`

## Advanced Usage

### Batch Processing Multiple PDFs
```bash
python -m pdf_form_editor batch forms/*.pdf --output processed/
```

This will:
- Process all PDFs in the `forms/` directory
- Save results to the `processed/` directory
- Generate a summary report of all processing

### Custom Configuration
```bash
python -m pdf_form_editor process form.pdf --config custom_config.yaml
```

Create `custom_config.yaml` to override default settings:
```yaml
processing:
  confidence_threshold: 0.9
  auto_approve_high_confidence: true

ai:
  model: "gpt-4"
  temperature: 0.05

naming:
  bem_strict_mode: true
  max_name_length: 80
```

### Claude Desktop Integration

Once the MCP server is implemented, you can use the tool directly in Claude Desktop:

1. **Upload PDF**: "I need to process this PDF form"
2. **Review Changes**: Claude shows an interactive table
3. **Make Adjustments**: "Change field 5 to 'owner-information_ssn'"  
4. **Download Result**: Get the processed PDF with one click

## Troubleshooting

### Common Issues

#### "No form fields found"
**Problem**: PDF doesn't have interactive form fields
**Solution**: 
- Open PDF in Adobe Acrobat
- Use "Prepare Form" to add interactive fields
- Or try a different PDF that already has form fields

#### "Permission denied" or "File in use"
**Problem**: PDF is open in another application
**Solution**:
- Close the PDF in Adobe Acrobat/Preview
- Check if any other applications have the file open
- Try copying the PDF to a new location

#### "OpenAI API error"
**Problem**: API key issues or rate limits
**Solutions**:
- Check your `.env` file has the correct `OPENAI_API_KEY`
- Verify you have API credits in your OpenAI account
- Try again in a few minutes if rate limited

#### "PDF corruption" warning
**Problem**: The PDF structure is unusual
**Solutions**:
- Try with a different PDF first to test the tool
- Use Adobe Acrobat to "Save As" a clean version
- Check the original PDF opens correctly

### Debug Mode

Run with verbose logging to see what's happening:
```bash
python -m pdf_form_editor process form.pdf --log-level DEBUG
```

This shows detailed information about:
- PDF parsing steps
- Field extraction process  
- AI API calls and responses
- Field naming decisions

### Getting Help

1. **Check the logs**: Look in `logs/pdf_form_editor.log`
2. **Try a simple PDF first**: Test with a basic form
3. **Check our examples**: Use the sample PDFs in `tests/fixtures/`
4. **Open an issue**: Report bugs on GitHub
5. **Read the docs**: Check `docs/api_reference.md` for technical details

## Best Practices

### For Best Results

1. **Use PDFs with clear labels**: Forms with visible field labels work best
2. **Consistent layout**: Well-organized forms get better results
3. **Review AI suggestions**: Always review before final approval
4. **Test with samples**: Try the tool on a few forms before batch processing
5. **Keep backups**: Original PDFs are never modified, but keep backups anyway

### BEM Naming Guidelines

1. **Keep it descriptive but concise**: `owner-information_name__first` not `owner-information_first-name-of-policy-owner`
2. **Use consistent patterns**: If you use `name__first`, also use `name__last`
3. **Group related fields**: Use the same block for related fields
4. **Avoid abbreviations**: Use `phone-number` not `phone-num`
5. **Be specific with modifiers**: `amount__gross` and `amount__net` not `amount1` and `amount2`

## Performance Tips

### Speed Up Processing
- **Use auto-approve**: Enable auto-approval for high-confidence suggestions
- **Batch similar forms**: Process similar forms together
- **Skip complex PDFs**: Start with simple, well-structured forms

### Improve Accuracy  
- **Add training data**: The tool learns from examples over time
- **Review and correct**: Your corrections help improve future suggestions
- **Use consistent terminology**: Standardize how you describe form sections

Your PDF form processing workflow is about to become 10x faster and more consistent! 🚀
'''

    # Comprehensive README
    comprehensive_readme = '''# PDF Form Enrichment Tool Documentation

This directory contains comprehensive documentation for the PDF Form Enrichment Tool.

## 📚 Documentation Files

### Development Documentation
- **[form_editor_task_list.md](form_editor_task_list.md)** - Complete development task list with detailed instructions
- **[form_field_editor_prd.md](form_field_editor_prd.md)** - Product Requirements Document for the core engine
- **[mcp_server_prd.md](mcp_server_prd.md)** - Product Requirements Document for Claude Desktop integration

### Reference Documentation  
- **[api_reference.md](api_reference.md)** - Complete API documentation with examples
- **[user_guide.md](user_guide.md)** - Step-by-step user guide and troubleshooting

### Additional Resources
- **[README.md](README.md)** - This overview document

## 🚀 Getting Started

1. **For Developers**: Start with `form_editor_task_list.md` to begin building
2. **For Users**: Read `user_guide.md` for usage instructions  
3. **For API Reference**: Check `api_reference.md` for technical details

## 🎯 Quick Links

### Development
- [Task 1.2: Basic PDF Reading](form_editor_task_list.md#task-12-basic-pdf-reading--structure-analysis)
- [BEM Naming Engine](form_editor_task_list.md#task-21-bem-naming-rules-engine)
- [AI Integration](form_editor_task_list.md#task-22-ai-integration-openai)

### Usage
- [Quick Start Guide](user_guide.md#quick-start)
- [BEM Naming Examples](user_guide.md#bem-naming-examples)
- [Troubleshooting](user_guide.md#troubleshooting)

### Reference
- [Core Classes](api_reference.md#core-classes)
- [CLI Commands](api_reference.md#cli-commands)
- [Configuration Options](api_reference.md#configuration)

## 🏗️ Project Overview

The PDF Form Enrichment Tool transforms manual PDF form processing from a 2-4 hour task into a 5-10 minute automated workflow using:

- **AI-powered field analysis** for intelligent naming
- **BEM naming convention** for consistent API field names
- **Safe PDF modification** that preserves document integrity
- **Interactive review interface** for human oversight
- **Claude Desktop integration** for conversational processing

## 🎉 Ready to Start?

Begin with the development task list and start building your PDF processing superpower! 🚀
'''

    files = {
        "docs/form_editor_task_list.md": task_list_content,
        "docs/form_field_editor_prd.md": prd_content,
        "docs/mcp_server_prd.md": mcp_prd_content,
        "docs/api_reference.md": api_reference_content,
        "docs/user_guide.md": user_guide_content,
        "docs/README.md": comprehensive_readme,
    }
    
    for filepath, content in files.items():
        create_file_with_content(filepath, content)

def main():
    print("📚 Adding Comprehensive Documentation...")
    print("=" * 50)
    
    # Check if we're in the right place
    if not Path(".git").exists():
        print("❌ Error: This doesn't look like a Git repository.")
        print("💡 Make sure you're in your project directory!")
        return
    
    print("📄 Creating comprehensive documentation files...")
    add_comprehensive_documentation()
    
    print("\n" + "=" * 50)
    print("🎉 Comprehensive documentation added!")
    print("\n📚 You now have:")
    print("  ✅ Complete task list with detailed instructions")
    print("  ✅ Product Requirements Documents (PRDs)")
    print("  ✅ API reference documentation")
    print("  ✅ Comprehensive user guide")
    print("  ✅ Development guidelines and examples")
    
    print("\n🎯 Next steps:")
    print("1. Read: docs/form_editor_task_list.md")
    print("2. Start with Task 1.2: Basic PDF Reading")
    print("3. Follow the step-by-step instructions")
    print("4. Use Claude Code to help implement each task")
    
    print("\n💾 Don't forget to commit your docs:")
    print("   git add docs/")
    print("   git commit -m 'Add comprehensive documentation'")
    print("   git push origin main")
    
    print("\n🚀 Ready to build your PDF processing superpower!")

if __name__ == "__main__":
    main()