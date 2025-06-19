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
        
        if review:
            click.echo("\n⚙️ Review mode enabled")
            click.echo(analyzer.get_summary())
        
        click.echo("\n🎯 Next steps:")
        click.echo("1. ✅ Task 1.2 completed - PDF parsing working!")
        click.echo("2. 🚧 Next: Implement Task 1.3 - Form field extraction")
        click.echo("3. 🚧 Then: Add AI integration for BEM naming")
        
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
