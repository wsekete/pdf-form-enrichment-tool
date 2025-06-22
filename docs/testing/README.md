# Testing Documentation

This directory contains comprehensive testing documentation and strategies for the PDF Form Enrichment Tool.

## Testing Philosophy

**Every test must show EVERY SINGLE FIELD from each PDF for complete verification and transparency.**

## Standard Test Script

Use `tests/test_complete_verification.py` as the template for all testing:

```bash
python tests/test_complete_verification.py
```

This script demonstrates the required testing standards:
- ✅ Shows ALL fields without omission
- ✅ Preservation mode enabled by default  
- ✅ Comprehensive statistical analysis
- ✅ Real-world PDF forms (no mocks)
- ✅ Production-ready performance metrics

## Required Test Output Format

```
🔍 COMPLETE VERIFICATION: [Form Name]
📄 File: [PDF Path]
🎯 Showing EVERY SINGLE FIELD - No Limits

📊 PRESERVATION STATISTICS (ALL FIELDS):
   • Total Fields: [N]
   • Preserved: [N] ([%])
   • Improved: [N] ([%])
   • Restructured: [N] ([%])
   • Success Rate: [%]

[Complete tabular output showing ALL fields]

✅ VERIFICATION COMPLETE: ALL [N] FIELDS SHOWN ABOVE
```

## Testing Standards

1. **Complete Field Verification**: Show all fields without limits
2. **Preservation Mode Required**: Always use `--preservation-mode`
3. **Real-World Forms**: Use actual PDFs, not mocks
4. **Tabular Output**: Show field IDs, names, types, confidence
5. **Statistical Analysis**: Preservation/improvement rates
6. **Performance Metrics**: Processing time, success rates
7. **Training Data Validation**: Confirm 4,838+ examples loaded

## Test Coverage Requirements

- Simple forms (W-4R): Basic field validation
- Complex forms (FAFF-0009AO.13): Radio button hierarchies  
- Desktop forms (LIFE-1528-Q_BLANK): Mixed field types
- CLI integration: `--preservation-mode` functionality
- Performance: <5 seconds per form
- Training data: 4,838+ examples integration

This ensures complete transparency and verification of the preservation mode BEM generation system.