#!/usr/bin/env python3
"""
PDF Analyzer - Core PDF parsing and analysis functionality

This module provides the PDFAnalyzer class for reading PDF files,
extracting metadata, and validating PDF structure.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..utils.errors import PDFProcessingError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PDFAnalyzer:
    """
    Analyzes PDF files to extract metadata and validate structure.
    
    This class handles PDF file loading, validation, and metadata extraction
    with comprehensive error handling for various PDF formats and conditions.
    """
    
    def __init__(self, file_path: Union[str, Path], password: Optional[str] = None):
        """
        Initialize PDFAnalyzer with a PDF file.
        
        Args:
            file_path: Path to the PDF file
            password: Password for encrypted PDFs (optional)
            
        Raises:
            PDFProcessingError: If PDF cannot be loaded or validated
        """
        self.file_path = Path(file_path)
        self.password = password
        self.reader: Optional[PdfReader] = None
        self._metadata_cache: Optional[Dict[str, Any]] = None
        
        # Validate file exists
        if not self.file_path.exists():
            raise PDFProcessingError(f"PDF file not found: {self.file_path}")
        
        # Load the PDF
        self._load_pdf()
    
    def _load_pdf(self) -> None:
        """
        Load PDF with comprehensive error handling.
        
        Raises:
            PDFProcessingError: If PDF cannot be loaded
        """
        try:
            logger.info(f"Loading PDF: {self.file_path}")
            self.reader = PdfReader(str(self.file_path))
            
            # Handle encrypted PDFs
            if self.reader.is_encrypted:
                if self.password:
                    logger.info("PDF is encrypted, attempting to decrypt")
                    success = self.reader.decrypt(self.password)
                    if not success:
                        raise PDFProcessingError("Invalid password for encrypted PDF")
                    logger.info("Successfully decrypted PDF")
                else:
                    raise PDFProcessingError(
                        "PDF is encrypted but no password provided. "
                        "Please provide password to access this file."
                    )
            
            # Validate PDF structure
            if not self.validate_pdf():
                raise PDFProcessingError("PDF structure validation failed")
                
            logger.info(f"Successfully loaded PDF with {len(self.reader.pages)} pages")
            
        except PdfReadError as e:
            raise PDFProcessingError(f"Invalid or corrupted PDF file: {str(e)}")
        except Exception as e:
            raise PDFProcessingError(f"Unexpected error loading PDF: {str(e)}")
    
    def validate_pdf(self) -> bool:
        """
        Validate PDF structure and integrity.
        
        Checks for:
        - Valid PDF reader object
        - At least one page
        - Readable content
        - Valid PDF structure elements
        
        Returns:
            bool: True if PDF is valid, False otherwise
        """
        try:
            if not self.reader:
                logger.error("No PDF reader object available")
                return False
            
            # Check if PDF has pages
            page_count = len(self.reader.pages)
            if page_count == 0:
                logger.error("PDF contains no pages")
                return False
            
            # Check if we can access the first page
            try:
                first_page = self.reader.pages[0]
                # Try to extract some content to ensure readability
                first_page.extract_text()
            except Exception as e:
                logger.error(f"Cannot access PDF content: {str(e)}")
                return False
            
            # Validate PDF structure components
            if not hasattr(self.reader, 'trailer') or not self.reader.trailer:
                logger.warning("PDF trailer not found or invalid")
                # Don't fail validation for this - some PDFs might work without trailer access
            
            logger.info(f"PDF validation successful: {page_count} pages")
            return True
            
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            return False
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract comprehensive PDF metadata.
        
        Returns:
            Dict containing PDF metadata including:
            - Basic info (page count, encryption status, etc.)
            - Document properties (title, author, etc.)
            - Form field information
            - File information
        """
        if self._metadata_cache:
            return self._metadata_cache
        
        if not self.reader:
            return {}
        
        try:
            metadata = {
                # Basic file information
                "file_path": str(self.file_path),
                "file_size": self.file_path.stat().st_size,
                "file_name": self.file_path.name,
                
                # PDF structure information
                "page_count": len(self.reader.pages),
                "is_encrypted": self.reader.is_encrypted,
                "has_form_fields": self.has_form_fields(),
                "pdf_version": self.get_pdf_version(),
                
                # Document properties
                "document_info": self._extract_document_info(),
                
                # Form information
                "form_info": self._extract_form_info(),
                
                # Validation status
                "is_valid": self.validate_pdf(),
                "analyzed_at": datetime.now().isoformat()
            }
            
            # Cache the metadata
            self._metadata_cache = metadata
            logger.info("Successfully extracted PDF metadata")
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {
                "file_path": str(self.file_path),
                "error": str(e),
                "is_valid": False
            }
    
    def _extract_document_info(self) -> Dict[str, Any]:
        """Extract document information from PDF metadata."""
        doc_info = {}
        
        try:
            if self.reader.metadata:
                # Common metadata fields
                metadata_fields = {
                    '/Title': 'title',
                    '/Author': 'author',
                    '/Subject': 'subject',
                    '/Creator': 'creator',
                    '/Producer': 'producer',
                    '/CreationDate': 'creation_date',
                    '/ModDate': 'modification_date',
                    '/Keywords': 'keywords'
                }
                
                for pdf_key, json_key in metadata_fields.items():
                    if pdf_key in self.reader.metadata:
                        value = self.reader.metadata[pdf_key]
                        # Convert to string for JSON serialization
                        doc_info[json_key] = str(value) if value else None
                        
        except Exception as e:
            logger.warning(f"Could not extract document info: {str(e)}")
            doc_info['extraction_error'] = str(e)
        
        return doc_info
    
    def _extract_form_info(self) -> Dict[str, Any]:
        """Extract form-related information from PDF."""
        form_info = {
            "has_acroform": False,
            "field_count": 0,
            "form_type": "none"
        }
        
        try:
            if not self.reader:
                return form_info
            
            # Check for AcroForm
            if not self.reader.trailer:
                return form_info
            catalog = self.reader.trailer.get("/Root")
            if catalog and "/AcroForm" in catalog:
                form_info["has_acroform"] = True
                form_info["form_type"] = "acroform"
                
                # Try to count fields
                acro_form = catalog["/AcroForm"]
                if "/Fields" in acro_form:
                    try:
                        field_count = len(acro_form["/Fields"])
                        form_info["field_count"] = field_count
                    except:
                        form_info["field_count"] = "unknown"
            
            # Check for XFA forms
            if catalog and "/AcroForm" in catalog:
                acro_form = catalog["/AcroForm"]
                if "/XFA" in acro_form:
                    form_info["form_type"] = "xfa"
                    form_info["has_xfa"] = True
                    
        except Exception as e:
            logger.warning(f"Could not extract form info: {str(e)}")
            form_info['extraction_error'] = str(e)
        
        return form_info
    
    def get_page_count(self) -> int:
        """Get number of pages in PDF."""
        return len(self.reader.pages) if self.reader else 0
    
    def has_form_fields(self) -> bool:
        """
        Check if PDF contains form fields.
        
        Returns:
            bool: True if PDF has form fields, False otherwise
        """
        if not self.reader:
            return False
        
        try:
            # Check for AcroForm in document catalog
            if not self.reader.trailer:
                return False
            catalog = self.reader.trailer.get("/Root")
            if catalog and "/AcroForm" in catalog:
                acro_form = catalog["/AcroForm"]
                # Check if fields array exists and has content
                if "/Fields" in acro_form:
                    fields = acro_form["/Fields"]
                    return len(fields) > 0 if fields else False
            return False
            
        except Exception as e:
            logger.warning(f"Error checking for form fields: {str(e)}")
            return False
    
    def is_encrypted(self) -> bool:
        """Check if PDF is encrypted."""
        return self.reader.is_encrypted if self.reader else False
    
    def get_pdf_version(self) -> str:
        """
        Get PDF version string.
        
        Returns:
            str: PDF version (e.g., "1.4", "1.7") or "Unknown"
        """
        if not self.reader:
            return "Unknown"
        
        try:
            # Try to get version from PDF header (PyPDF 3.0+)
            if hasattr(self.reader, 'pdf_header') and self.reader.pdf_header:
                header = self.reader.pdf_header
                # Extract version number from header like "%PDF-1.5"
                if header.startswith('%PDF-'):
                    version = header[5:].strip()  # Remove prefix and whitespace
                    return version if version else "Unknown"
                return header
            
            # Fallback to checking the catalog version
            if self.reader.trailer:
                catalog = self.reader.trailer.get("/Root")
                if catalog and "/Version" in catalog:
                    return str(catalog["/Version"])
            
            return "Unknown"
            
        except Exception as e:
            logger.warning(f"Could not determine PDF version: {str(e)}")
            return "Unknown"
    
    def export_metadata_json(self, output_path: Union[str, Path]) -> None:
        """
        Export metadata to JSON file.
        
        Args:
            output_path: Path where to save the JSON file
            
        Raises:
            PDFProcessingError: If export fails
        """
        try:
            output_path = Path(output_path)
            metadata = self.extract_metadata()
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"Metadata exported to: {output_path}")
            
        except Exception as e:
            raise PDFProcessingError(f"Failed to export metadata: {str(e)}")
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of the PDF.
        
        Returns:
            str: Formatted summary of PDF information
        """
        if not self.reader:
            return "No PDF loaded"
        
        metadata = self.extract_metadata()
        
        summary_lines = [
            f"PDF Analysis Summary",
            f"=" * 20,
            f"File: {metadata.get('file_name', 'Unknown')}",
            f"Size: {metadata.get('file_size', 0):,} bytes",
            f"Pages: {metadata.get('page_count', 0)}",
            f"Version: {metadata.get('pdf_version', 'Unknown')}",
            f"Encrypted: {'Yes' if metadata.get('is_encrypted') else 'No'}",
            f"Has Forms: {'Yes' if metadata.get('has_form_fields') else 'No'}",
        ]
        
        # Add form information if available
        form_info = metadata.get('form_info', {})
        if form_info.get('has_acroform'):
            summary_lines.append(f"Form Fields: {form_info.get('field_count', 'Unknown')}")
        
        # Add document info if available
        doc_info = metadata.get('document_info', {})
        if doc_info.get('title'):
            summary_lines.append(f"Title: {doc_info['title']}")
        if doc_info.get('author'):
            summary_lines.append(f"Author: {doc_info['author']}")
        
        return "\n".join(summary_lines)