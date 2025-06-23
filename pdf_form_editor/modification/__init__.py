"""
PDF Field Modification Module

This module provides comprehensive PDF field modification capabilities with:
- Safe field name updates while preserving functionality
- Hierarchy and relationship management
- Backup and recovery systems
- Comprehensive validation and integrity checking
- Multi-format output generation
"""

from .pdf_modifier import SafePDFModifier, ModificationPlan, ModificationResult, FieldModification
from .hierarchy_manager import HierarchyManager, HierarchyTree, HierarchyNode
from .backup_recovery import BackupRecoverySystem, BackupInfo, RestoreResult
from .integrity_validator import PDFIntegrityValidator, IntegrityReport
from .output_generator import ComprehensiveOutputGenerator, OutputPackage
from .modification_tracker import ModificationTracker

__all__ = [
    'SafePDFModifier',
    'HierarchyManager', 
    'BackupRecoverySystem',
    'PDFIntegrityValidator',
    'ComprehensiveOutputGenerator',
    'ModificationTracker',
    'ModificationPlan',
    'ModificationResult',
    'FieldModification',
    'HierarchyTree',
    'HierarchyNode',
    'BackupInfo',
    'RestoreResult',
    'IntegrityReport',
    'OutputPackage'
]