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
from .core.field_extractor import FieldExtractor, ContextExtractor
from .training.data_loader import TrainingDataLoader
from .training.pattern_analyzer import PatternAnalyzer
from .training.similarity_matcher import SimilarityMatcher
from .naming.bem_generator import BEMNameGenerator
from .naming.pattern_learner import PatternLearner
from .naming.rule_engine import RuleBasedEngine
from .naming.name_validator import BEMNameValidator
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
                        
                        # Extract context information for all fields
                        context_extractor = ContextExtractor(analyzer)
                        contexts = context_extractor.extract_all_contexts(fields)
                        
                        fields_data = {
                            "fields": [
                                {
                                    "id": field.id,
                                    "name": field.name,
                                    "type": field.field_type,
                                    "page": field.page,
                                    "rect": field.rect,
                                    "value": field.value,
                                    "properties": field.properties,
                                    "context": {
                                        "label": contexts[field.id].label,
                                        "section_header": contexts[field.id].section_header,
                                        "confidence": contexts[field.id].confidence,
                                        "visual_group": contexts[field.id].visual_group,
                                        "nearby_text": contexts[field.id].nearby_text,
                                        "directional_text": {
                                            "above": contexts[field.id].text_above,
                                            "below": contexts[field.id].text_below,
                                            "left": contexts[field.id].text_left,
                                            "right": contexts[field.id].text_right
                                        }
                                    } if field.id in contexts else None
                                }
                                for field in fields
                            ],
                            "statistics": extractor.get_field_statistics(fields),
                            "validation": extractor.validate_field_structure(fields),
                            "context_analysis": {
                                "total_fields": len(fields),
                                "fields_with_context": len(contexts),
                                "average_confidence": sum(ctx.confidence for ctx in contexts.values()) / len(contexts) if contexts else 0,
                                "context_extraction_timestamp": str(Path().cwd())  # Simple timestamp placeholder
                            }
                        }
                        with open(fields_file, 'w') as f:
                            json.dump(fields_data, f, indent=2, default=str)
                        click.echo(f"📝 Field data exported to: {fields_file}")
                except Exception as e:
                    click.echo(f"⚠️  Field export failed: {e}")
        
        if review:
            click.echo("\n⚙️ Review mode enabled")
            click.echo(analyzer.get_summary())
        
        click.echo("\n🎯 Phase 1 Progress:")
        click.echo("1. ✅ Task 1.1 completed - Project setup & environment")
        click.echo("2. ✅ Task 1.2 completed - PDF parsing & analysis")
        click.echo("3. ✅ Task 1.3 completed - Form field extraction with radio button hierarchy")
        click.echo("4. ✅ Task 1.4 completed - Field context extraction (use --context flag)")
        click.echo("\n🚀 Ready for Phase 2: AI integration for BEM naming!")
        
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
@click.option("--context", "-c", is_flag=True, help="Extract field context information")
@click.pass_context
def analyze(ctx: click.Context, pdf_path: str, password: str, export: str, context: bool):
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
                    
                    # Extract context information if requested
                    if context:
                        click.echo(f"\n🔍 Context Analysis (Task 1.4):")
                        try:
                            context_extractor = ContextExtractor(analyzer)
                            contexts = context_extractor.extract_all_contexts(fields[:5])  # Sample first 5 fields
                            
                            total_confidence = sum(ctx.confidence for ctx in contexts.values())
                            avg_confidence = total_confidence / len(contexts) if contexts else 0
                            
                            click.echo(f"  📊 Average Context Confidence: {avg_confidence:.2f}")
                            click.echo(f"  🔍 Context extracted for {len(contexts)} sample fields")
                            
                            if verbose and contexts:
                                click.echo(f"\n📋 Sample Context Details:")
                                for field_id, ctx in list(contexts.items())[:3]:  # Show first 3
                                    field = next(f for f in fields if f.id == field_id)
                                    click.echo(f"    📝 {field.name} ({field.field_type}):")
                                    click.echo(f"      Label: '{ctx.label}' (confidence: {ctx.confidence:.2f})")
                                    click.echo(f"      Section: '{ctx.section_header}'")
                                    click.echo(f"      Visual Group: {ctx.visual_group}")
                                    if ctx.nearby_text:
                                        click.echo(f"      Nearby Text: {ctx.nearby_text[:2]}")
                                    click.echo()
                            
                        except Exception as e:
                            click.echo(f"  ⚠️  Context extraction failed: {e}")
                
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
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--training-data", "-t", default="./samples", help="Training data directory")
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--confidence-threshold", "-c", default=0.8, help="Minimum confidence for auto-approval")
@click.option("--review", "-r", is_flag=True, help="Enable interactive review")
@click.option("--format", "-f", default="all", help="Output format: csv, json, all")
@click.option("--validate-only", is_flag=True, help="Only validate generated names without saving")
@click.option("--preservation-mode", "-p", is_flag=True, help="Use preservation mode for existing good names")
@click.pass_context
def generate_names(ctx: click.Context, pdf_path: str, training_data: str, output: str, 
                  confidence_threshold: float, review: bool, format: str, validate_only: bool, preservation_mode: bool):
    """Generate BEM names using training data and context analysis."""
    
    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        setup_logging("DEBUG")
    else:
        setup_logging("INFO")
    
    try:
        click.echo(f"🎯 Generating BEM names for: {pdf_path}")
        click.echo(f"📚 Using training data from: {training_data}")
        
        # Step 1: Load and analyze PDF
        click.echo("\n📄 Step 1: Loading and analyzing PDF...")
        analyzer = PDFAnalyzer(pdf_path)
        
        if not analyzer.has_form_fields():
            click.echo("❌ No form fields found in this PDF")
            return
        
        # Step 2: Extract fields and context
        click.echo("🔍 Step 2: Extracting fields and context...")
        field_extractor = FieldExtractor(analyzer)
        fields = field_extractor.extract_form_fields()
        
        context_extractor = ContextExtractor(analyzer)
        contexts = context_extractor.extract_all_contexts(fields)
        
        click.echo(f"✅ Found {len(fields)} fields with context data")
        
        # Step 3: Load training data and build patterns
        click.echo("📚 Step 3: Loading training data and building patterns...")
        try:
            # Load training data
            data_loader = TrainingDataLoader(training_data)
            
            # Load FormField examples for comprehensive pattern learning
            formfield_examples = data_loader.load_formfield_examples(f"{training_data}/FormField_examples.csv")
            click.echo(f"✅ Loaded {len(formfield_examples)} FormField examples")
            
            # Load training pairs
            training_pairs = data_loader.discover_training_pairs()
            training_examples = []
            
            for pair in training_pairs[:3]:  # Limit to avoid overwhelming processing
                try:
                    example = data_loader.load_training_pair(pair.pdf_path, pair.csv_path)
                    training_examples.append(example)
                except Exception as e:
                    click.echo(f"⚠️  Failed to load pair {pair.pair_id}: {e}")
            
            click.echo(f"✅ Loaded {len(training_examples)} training pairs")
            
            # Combine all training data
            all_training_mappings = formfield_examples
            for example in training_examples:
                all_training_mappings.extend(example.csv_mappings)
            
            click.echo(f"✅ Total training examples: {len(all_training_mappings)}")
            
            if preservation_mode:
                click.echo("🛡️  Preservation mode enabled - will intelligently preserve good existing names")
        
        except Exception as e:
            click.echo(f"⚠️  Training data loading failed: {e}")
            click.echo("🔄 Falling back to rule-based generation")
            all_training_mappings = []
        
        # Step 4: Initialize BEM generator
        click.echo("🤖 Step 4: Initializing BEM name generator...")
        
        if preservation_mode and all_training_mappings:
            # Use preservation mode with training data
            from .naming.preservation_generator import PreservationBEMGenerator
            preservation_generator = PreservationBEMGenerator(all_training_mappings)
            
            click.echo("🛡️  Using preservation mode with intelligent improvements")
            
            # Step 5: Analyze and generate BEM names with preservation
            click.echo("⚡ Step 5: Analyzing existing names and generating improvements...")
            bem_results = []
            generated_names = []
            
            preservation_stats = {"preserved": 0, "improved": 0, "restructured": 0}
            
            with click.progressbar(fields, label="Analyzing names") as progress_fields:
                for field in progress_fields:
                    field_context = contexts.get(field.id)
                    if field_context:
                        analysis = preservation_generator.analyze_field_name(field, field_context)
                        
                        # Convert to BEMResult for compatibility
                        from .naming.bem_generator import BEMResult, GenerationMethod
                        result = BEMResult(
                            bem_name=analysis.suggested_name,
                            confidence=analysis.confidence,
                            generation_method=GenerationMethod.EXACT_PATTERN_MATCH if analysis.action.value == "preserve" else GenerationMethod.SIMILAR_CONTEXT_ADAPTATION,
                            reasoning=analysis.reasoning,
                            field_id=field.id
                        )
                        
                        bem_results.append(result)
                        generated_names.append(result.bem_name)
                        preservation_stats[analysis.action.value] += 1
            
            click.echo(f"📊 Preservation Analysis: {preservation_stats['preserved']} preserved, "
                      f"{preservation_stats['improved']} improved, {preservation_stats['restructured']} restructured")
        
        else:
            # Use regular generation mode
            from .training.pattern_analyzer import PatternDatabase
            pattern_database = PatternDatabase() 
            similarity_matcher = SimilarityMatcher(pattern_database)
            bem_generator = BEMNameGenerator(pattern_database, similarity_matcher)
            
            click.echo("⚡ Step 5: Generating BEM names...")
            bem_results = []
            generated_names = []
            
            with click.progressbar(fields, label="Generating names") as progress_fields:
                for field in progress_fields:
                    field_context = contexts.get(field.id)
                    if field_context:
                        result = bem_generator.generate_bem_name(field, field_context)
                        bem_results.append(result)
                        generated_names.append(result.bem_name)
        
        validator = BEMNameValidator()
        
        # Step 6: Validate generated names
        click.echo("✅ Step 6: Validating generated names...")
        validation_results = validator.validate_batch(generated_names)
        summary = validator.get_validation_summary(validation_results)
        
        click.echo(f"📊 Validation Results:")
        click.echo(f"  • Total names: {summary['total_names']}")
        click.echo(f"  • Valid names: {summary['valid_names']}")
        click.echo(f"  • Success rate: {summary['success_rate']:.1%}")
        click.echo(f"  • Average confidence: {sum(r.confidence for r in bem_results) / len(bem_results):.2f}")
        
        # Display results
        if verbose or review:
            click.echo("\n📋 Generated BEM Names:")
            for field, result in zip(fields, bem_results):
                status = "✅" if validation_results[result.bem_name].is_valid else "❌"
                confidence_indicator = "🟢" if result.confidence > 0.8 else "🟡" if result.confidence > 0.5 else "🔴"
                click.echo(f"  {status} {confidence_indicator} {field.name} → {result.bem_name} "
                          f"({result.confidence:.2f})")
                
                if verbose:
                    click.echo(f"      Method: {result.generation_method.value}")
                    click.echo(f"      Reason: {result.reasoning}")
        
        # Step 7: Handle review mode
        if review and not validate_only:
            click.echo("\n🔍 Interactive Review Mode")
            approved_results = []
            
            for field, result in zip(fields, bem_results):
                click.echo(f"\n📝 Field: {field.name} ({field.field_type})")
                click.echo(f"🎯 Generated: {result.bem_name}")
                click.echo(f"📊 Confidence: {result.confidence:.2f}")
                click.echo(f"💡 Reasoning: {result.reasoning}")
                
                if result.alternatives:
                    click.echo("🔄 Alternatives:")
                    for i, alt in enumerate(result.alternatives[:3], 1):
                        click.echo(f"   {i}. {alt.bem_name} ({alt.confidence:.2f})")
                
                choice = click.prompt("Action: (a)pprove, (r)eject, (m)odify, (s)kip", 
                                    type=click.Choice(['a', 'r', 'm', 's']), default='a')
                
                if choice == 'a':
                    approved_results.append(result)
                elif choice == 'm':
                    custom_name = click.prompt("Enter custom BEM name")
                    result.bem_name = custom_name
                    result.confidence = 1.0  # User-approved
                    approved_results.append(result)
                elif choice == 's':
                    continue
                # 'r' means reject, so don't add to approved
            
            bem_results = approved_results
            click.echo(f"\n✅ Approved {len(approved_results)} names for export")
        
        # Step 8: Export results
        if output and not validate_only:
            click.echo(f"\n📁 Step 8: Exporting results to {output}...")
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            base_name = Path(pdf_path).stem
            
            # Export JSON metadata
            if format in ['json', 'all']:
                json_file = output_dir / f"{base_name}_bem_names.json"
                export_data = {
                    "pdf_file": pdf_path,
                    "generation_timestamp": str(Path().cwd()),  # Simple timestamp
                    "total_fields": len(fields),
                    "generated_names": len(bem_results),
                    "average_confidence": sum(r.confidence for r in bem_results) / len(bem_results) if bem_results else 0,
                    "validation_summary": summary,
                    "results": [
                        {
                            "field_id": field.id,
                            "field_name": field.name,
                            "field_type": field.field_type,
                            "bem_name": result.bem_name,
                            "confidence": result.confidence,
                            "generation_method": result.generation_method.value,
                            "reasoning": result.reasoning,
                            "validation": {
                                "is_valid": validation_results[result.bem_name].is_valid,
                                "errors": validation_results[result.bem_name].errors,
                                "warnings": validation_results[result.bem_name].warnings
                            }
                        }
                        for field, result in zip(fields, bem_results)
                    ]
                }
                
                with open(json_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                click.echo(f"📄 JSON exported to: {json_file}")
            
            # Export CSV format (simplified)
            if format in ['csv', 'all']:
                csv_file = output_dir / f"{base_name}_bem_names.csv"
                with open(csv_file, 'w') as f:
                    f.write("field_name,field_type,bem_name,confidence,method,validation_status\n")
                    for field, result in zip(fields, bem_results):
                        validation_status = "valid" if validation_results[result.bem_name].is_valid else "invalid"
                        f.write(f'"{field.name}","{field.field_type}","{result.bem_name}",'
                               f'{result.confidence},"{result.generation_method.value}","{validation_status}"\n')
                
                click.echo(f"📊 CSV exported to: {csv_file}")
        
        # Final summary
        click.echo(f"\n🎉 BEM Name Generation Complete!")
        click.echo(f"📊 Generated {len(bem_results)} BEM names")
        click.echo(f"✅ {summary['valid_names']} names passed validation")
        click.echo(f"📈 {summary['success_rate']:.1%} success rate")
        
        if summary['success_rate'] < 0.8:
            click.echo("\n💡 Suggestions to improve success rate:")
            click.echo("  • Add more training data examples")
            click.echo("  • Review field context extraction")
            click.echo("  • Use interactive review mode (-r)")
        
    except Exception as e:
        click.echo(f"❌ BEM generation error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--data-directory", "-d", default="./training_data", help="Training data location")
@click.option("--validate", "-v", is_flag=True, help="Validate training data quality")
@click.option("--report", "-r", type=click.Path(), help="Generate analysis report")
@click.pass_context
def train(ctx: click.Context, data_directory: str, validate: bool, report: str):
    """Load and analyze training data for pattern learning."""
    
    verbose = ctx.obj.get("verbose", False)
    
    if verbose:
        setup_logging("DEBUG")
    
    try:
        click.echo(f"📚 Analyzing training data from: {data_directory}")
        
        # Load training data
        data_loader = TrainingDataLoader(data_directory)
        training_pairs = data_loader.discover_training_pairs()
        
        if not training_pairs:
            click.echo("❌ No training data found in the specified directory")
            return
        
        click.echo(f"✅ Found {len(training_pairs)} training pairs")
        
        # Load and validate training examples
        training_examples = []
        for pair in training_pairs:
            try:
                example = data_loader.load_training_pair(pair.pdf_path, pair.csv_path)
                training_examples.append(example)
            except Exception as e:
                click.echo(f"⚠️  Failed to load {pair.pair_id}: {e}")
        
        click.echo(f"✅ Successfully loaded {len(training_examples)} training examples")
        
        if validate:
            click.echo("\n🔍 Validating training data quality...")
            validation_report = data_loader.validate_training_data(training_pairs)
            
            click.echo(f"📊 Validation Results:")
            click.echo(f"  • Valid pairs: {validation_report.valid_pairs}")
            click.echo(f"  • Invalid pairs: {validation_report.invalid_pairs}")
            click.echo(f"  • Success rate: {validation_report.success_rate:.1%}")
            
            if validation_report.issues:
                click.echo("⚠️  Issues found:")
                for issue in validation_report.issues[:5]:
                    click.echo(f"    • {issue}")
        
        # Analyze patterns
        click.echo("\n🔬 Analyzing naming patterns...")
        pattern_analyzer = PatternAnalyzer()
        pattern_database = pattern_analyzer.analyze_training_data(training_examples)
        
        click.echo(f"✅ Pattern Analysis Complete:")
        click.echo(f"  • Context patterns: {len(pattern_database.context_patterns)}")
        click.echo(f"  • Spatial patterns: {len(pattern_database.spatial_patterns)}")
        click.echo(f"  • Naming patterns: {len(pattern_database.naming_patterns)}")
        
        # Generate report
        if report or verbose:
            analysis_report = pattern_analyzer.generate_pattern_report(pattern_database)
            
            if verbose:
                click.echo(f"\n📋 Pattern Analysis Report:")
                click.echo(f"  📊 Total examples: {analysis_report.total_examples}")
                click.echo(f"  📝 Total fields: {analysis_report.total_fields}")
                click.echo(f"  🎯 Pattern coverage: {analysis_report.pattern_coverage}")
                click.echo(f"  📈 Confidence distribution: {analysis_report.confidence_distribution}")
                
                if analysis_report.common_blocks:
                    click.echo(f"  🏗️  Common blocks: {', '.join(analysis_report.common_blocks[:5])}")
                
                if analysis_report.recommendations:
                    click.echo(f"  💡 Recommendations:")
                    for rec in analysis_report.recommendations:
                        click.echo(f"    • {rec}")
            
            if report:
                with open(report, 'w') as f:
                    json.dump({
                        "analysis_report": {
                            "total_examples": analysis_report.total_examples,
                            "total_fields": analysis_report.total_fields,
                            "pattern_coverage": analysis_report.pattern_coverage,
                            "confidence_distribution": analysis_report.confidence_distribution,
                            "common_blocks": analysis_report.common_blocks,
                            "common_elements": analysis_report.common_elements,
                            "spatial_clusters": analysis_report.spatial_clusters,
                            "recommendations": analysis_report.recommendations
                        },
                        "pattern_database": {
                            "context_patterns": len(pattern_database.context_patterns),
                            "spatial_patterns": len(pattern_database.spatial_patterns),
                            "naming_patterns": len(pattern_database.naming_patterns)
                        }
                    }, f, indent=2)
                
                click.echo(f"📄 Analysis report exported to: {report}")
        
        click.echo(f"\n🎉 Training data analysis complete!")
        
    except Exception as e:
        click.echo(f"❌ Training analysis error: {e}", err=True)
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
    click.echo("\n🎯 Status: Ready for Task 2.2 - BEM Name Generation!")
    click.echo("📋 Available commands:")
    click.echo("  • analyze     - Analyze PDF structure and fields")
    click.echo("  • process     - Process PDF with basic field extraction")
    click.echo("  • generate-names - Generate BEM names using AI patterns (NEW!)")
    click.echo("  • train       - Analyze training data patterns (NEW!)")
    click.echo("  • info        - Show this information")
    click.echo("\n🚀 Phase 2 Progress:")
    click.echo("✅ Task 2.1: Training Data Integration - COMPLETED")
    click.echo("✅ Task 2.2: Context-Aware BEM Name Generator - COMPLETED")
    click.echo("⏳ Task 2.3: PDF Field Modification Engine - PENDING")
    click.echo("⏳ Task 2.4: Database-Ready Output Generation - PENDING")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
