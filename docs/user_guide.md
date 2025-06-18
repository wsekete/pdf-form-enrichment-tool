# PDF Form Enrichment Tool - User Guide

## Quick Start

### 1. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-form-enrichment-tool.git
cd pdf-form-enrichment-tool

# Set up environment
make setup
source venv/bin/activate  # Mac/Linux
# or: venv\Scripts\activate  # Windows

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
