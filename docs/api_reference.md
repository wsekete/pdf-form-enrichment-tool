# PDF Form Enrichment Tool - API Reference

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
