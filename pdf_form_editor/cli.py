#!/usr/bin/env python3
"""
Command Line Interface for PDF Form Enrichment Tool
"""

import os
import sys
from pathlib import Path

import click

from . import __version__
from .core.pdf_analyzer import PDFAnalyzer
from .core.field_extractor import FieldExtractor
from .utils.errors import PDFProcessingError
from .utils.logging import setup_logging


@click.group()
@click.version_option(version=__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """PDF Form Enrichment Tool - AI-powered BEM naming automation."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--review", "-r", is_flag=True, help="Enable interactive review mode")
@click.option("--password", "-p", help="Password for encrypted PDFs")
@click.pass_context
def process(ctx: click.Context, pdf_path: str, output: str, review: bool, password: str):
    """Process a single PDF form with BEM naming."""

    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        setup_logging("DEBUG")
    else:
        setup_logging("INFO")

    try:
        click.echo(f"📄 Processing PDF: {pdf_path}")
        
        # Initialize PDF analyzer
        analyzer = PDFAnalyzer(pdf_path, password)
        
        # Display basic information
        click.echo(f"✅ PDF loaded successfully")
        click.echo(f"📊 Pages: {analyzer.get_page_count()}")
        click.echo(f"🔒 Encrypted: {'Yes' if analyzer.is_encrypted() else 'No'}")
        click.echo(f"📝 Has Forms: {'Yes' if analyzer.has_form_fields() else 'No'}")
        
        if analyzer.has_form_fields():
            click.echo("🎯 Form fields detected - ready for BEM naming!")
            
            # Extract form fields
            extractor = FieldExtractor(analyzer)
            fields = extractor.extract_form_fields()
            
            if fields:
                click.echo(f"📝 Found {len(fields)} form fields:")
                stats = extractor.get_field_statistics(fields)
                
                # Display field type breakdown
                for field_type, count in stats["field_types"].items():
                    click.echo(f"  • {field_type}: {count} fields")
                
                click.echo(f"📊 Fields on {stats['pages_with_fields']} pages")
                click.echo(f"🔒 Required fields: {stats['required_fields']}")
                
                if verbose:
                    click.echo("\n📋 Field Details:")
                    for field in fields[:10]:  # Show first 10 fields
                        click.echo(f"  • {field.name} ({field.field_type}) - Page {field.page}")
                    if len(fields) > 10:
                        click.echo(f"  ... and {len(fields) - 10} more fields")
            else:
                click.echo("⚠️  No form fields could be extracted")
        else:
            click.echo("⚠️  No form fields found in this PDF")
        
        # Set up output directory
        if output:
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            click.echo(f"📁 Output directory: {output_dir}")
            
            # Export metadata
            metadata_file = output_dir / f"{Path(pdf_path).stem}_analysis.json"
            analyzer.export_metadata_json(metadata_file)
            click.echo(f"📋 Analysis exported to: {metadata_file}")
            
            # Export field data if available
            if analyzer.has_form_fields():
                try:
                    extractor = FieldExtractor(analyzer)
                    fields = extractor.extract_form_fields()
                    if fields:
                        fields_file = output_dir / f"{Path(pdf_path).stem}_fields.json"
                        import json
                        fields_data = {
                            "fields": [
                                {
                                    "id": field.id,
                                    "name": field.name,
                                    "type": field.field_type,
                                    "page": field.page,
                                    "rect": field.rect,
                                    "value": field.value,
                                    "properties": field.properties
                                }
                                for field in fields
                            ],
                            "statistics": extractor.get_field_statistics(fields),
                            "validation": extractor.validate_field_structure(fields)
                        }
                        with open(fields_file, 'w') as f:
                            json.dump(fields_data, f, indent=2, default=str)
                        click.echo(f"📝 Field data exported to: {fields_file}")
                except Exception as e:
                    click.echo(f"⚠️  Field export failed: {e}")
        
        if review:
            click.echo("\n⚙️ Review mode enabled")
            click.echo(analyzer.get_summary())
        
        click.echo("\n🎯 Next steps:")
        click.echo("1. ✅ Task 1.2 completed - PDF parsing working!")
        click.echo("2. ✅ Task 1.3 completed - Form field extraction working!")
        click.echo("3. 🚧 Next: Implement Task 1.4 - Field context extraction")
        click.echo("4. 🚧 Then: Add AI integration for BEM naming")
        
    except PDFProcessingError as e:
        click.echo(f"❌ PDF processing error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--password", "-p", help="Password for encrypted PDFs")
@click.option("--export", "-e", type=click.Path(), help="Export analysis to JSON file")
@click.pass_context
def analyze(ctx: click.Context, pdf_path: str, password: str, export: str):
    """Analyze PDF structure and form fields."""

    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        setup_logging("DEBUG")

    try:
        click.echo(f"📄 Analyzing PDF: {pdf_path}")
        
        # Initialize PDF analyzer
        analyzer = PDFAnalyzer(pdf_path, password)
        
        # Display comprehensive analysis
        click.echo(analyzer.get_summary())
        
        # Extract and display form fields if available
        if analyzer.has_form_fields():
            try:
                extractor = FieldExtractor(analyzer)
                fields = extractor.extract_form_fields()
                
                if fields:
                    click.echo(f"\n📝 Form Field Analysis ({len(fields)} fields):")
                    stats = extractor.get_field_statistics(fields)
                    
                    # Display statistics
                    click.echo(f"  📊 Field Types:")
                    for field_type, count in stats["field_types"].items():
                        click.echo(f"    • {field_type}: {count}")
                    
                    click.echo(f"  📄 Distribution: {stats['pages_with_fields']} pages with fields")
                    click.echo(f"  🔒 Required: {stats['required_fields']} fields")
                    click.echo(f"  📝 Filled: {stats['fields_with_values']} fields")
                    
                    # Show validation report
                    validation = extractor.validate_field_structure(fields)
                    click.echo(f"  ✅ Valid: {validation['valid_fields']}/{validation['total_fields']} fields")
                    
                    if validation['issues']:
                        click.echo(f"  ⚠️  Issues found:")
                        for issue in validation['issues'][:5]:  # Show first 5 issues
                            click.echo(f"    • {issue}")
                    
                    if verbose:
                        click.echo(f"\n📋 Field List:")
                        for field in fields:
                            req_indicator = "🔒" if field.is_required else "  "
                            click.echo(f"    {req_indicator} {field.name} ({field.field_type}) - Page {field.page}")
                            if field.value:
                                click.echo(f"      Value: {field.value}")
                
            except Exception as e:
                click.echo(f"⚠️  Field extraction failed: {e}")
        
        # Display detailed metadata if verbose
        if verbose:
            metadata = analyzer.extract_metadata()
            click.echo(f"\n📋 Detailed Metadata:")
            
            # Document info
            doc_info = metadata.get('document_info', {})
            if doc_info:
                click.echo(f"  📄 Document Properties:")
                for key, value in doc_info.items():
                    if value and key != 'extraction_error':
                        click.echo(f"    {key}: {value}")
            
            # Form info
            form_info = metadata.get('form_info', {})
            if form_info:
                click.echo(f"  📝 Form Properties:")
                for key, value in form_info.items():
                    if key != 'extraction_error':
                        click.echo(f"    {key}: {value}")
        
        # Export if requested
        if export:
            analyzer.export_metadata_json(export)
            click.echo(f"📁 Analysis exported to: {export}")
            
        click.echo(f"\n✅ Analysis complete!")
        
    except PDFProcessingError as e:
        click.echo(f"❌ PDF analysis error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.pass_context
def info(ctx: click.Context):
    """Show system information and configuration."""

    click.echo(f"🔧 PDF Form Enrichment Tool v{__version__}")
    click.echo(f"📍 Python: {sys.version}")
    click.echo(f"📁 Working directory: {os.getcwd()}")
    click.echo("\n🎯 Status: Ready for development!")
    click.echo("📋 Follow docs/form_editor_task_list.md to start building")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
