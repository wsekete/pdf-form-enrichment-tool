#!/usr/bin/env python3
"""
Backup and Recovery System for PDF Modifications

Provides comprehensive backup and recovery capabilities for safe PDF modifications
with automatic rollback on failures and detailed backup management.
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from ..utils.logging import get_logger
from ..utils.errors import PDFProcessingError

logger = get_logger(__name__)


@dataclass
class BackupInfo:
    """Information about a PDF backup."""
    backup_id: str
    original_pdf: str
    backup_path: str
    created_at: datetime
    file_size: int
    modification_count: int
    notes: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupInfo':
        """Create from dictionary loaded from JSON."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class RestoreResult:
    """Result of a backup restoration operation."""
    success: bool
    restored_path: str
    backup_info: BackupInfo
    errors: List[str]


@dataclass
class CleanupResult:
    """Result of backup cleanup operation."""
    backups_removed: int
    space_reclaimed_mb: float
    errors: List[str]


class BackupRecoverySystem:
    """Comprehensive backup and recovery for PDF modifications."""
    
    def __init__(self, work_directory: str = "./backups"):
        """
        Initialize backup system.
        
        Args:
            work_directory: Directory to store backups and metadata
        """
        self.backup_dir = Path(work_directory)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self._load_metadata()
        
        logger.info(f"BackupRecoverySystem initialized with directory: {self.backup_dir}")
    
    def _load_metadata(self) -> None:
        """Load backup metadata from storage."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.metadata = {
                        backup_id: BackupInfo.from_dict(info)
                        for backup_id, info in data.items()
                    }
            else:
                self.metadata = {}
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
            self.metadata = {}
    
    def _save_metadata(self) -> None:
        """Save backup metadata to storage."""
        try:
            data = {
                backup_id: info.to_dict()
                for backup_id, info in self.metadata.items()
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")
    
    def create_backup(self, pdf_path: str, notes: str = "") -> BackupInfo:
        """
        Create timestamped backup with metadata.
        
        Args:
            pdf_path: Path to the PDF file to backup
            notes: Optional notes about this backup
            
        Returns:
            BackupInfo with details about the created backup
            
        Raises:
            PDFProcessingError: If backup creation fails
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise PDFProcessingError(f"PDF file not found: {pdf_path}")
            
            # Generate backup ID and path
            timestamp = datetime.now()
            backup_id = f"{pdf_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / f"{backup_id}_backup.pdf"
            
            # Copy PDF file
            shutil.copy2(pdf_path, backup_path)
            
            # Create backup info
            backup_info = BackupInfo(
                backup_id=backup_id,
                original_pdf=str(pdf_path),
                backup_path=str(backup_path),
                created_at=timestamp,
                file_size=backup_path.stat().st_size,
                modification_count=0,
                notes=notes,
                metadata={
                    "original_size": pdf_path.stat().st_size,
                    "backup_type": "full"
                }
            )
            
            # Store metadata
            self.metadata[backup_id] = backup_info
            self._save_metadata()
            
            logger.info(f"Created backup: {backup_id} for {pdf_path}")
            return backup_info
            
        except Exception as e:
            raise PDFProcessingError(f"Failed to create backup for {pdf_path}: {e}")
    
    def create_incremental_backup(self, pdf_path: str, modification_count: int, notes: str = "") -> BackupInfo:
        """
        Create incremental backup during modification process.
        
        Args:
            pdf_path: Path to the PDF file to backup
            modification_count: Number of modifications applied so far
            notes: Optional notes about this backup state
            
        Returns:
            BackupInfo with details about the created backup
        """
        backup_info = self.create_backup(pdf_path, notes)
        backup_info.modification_count = modification_count
        backup_info.metadata["backup_type"] = "incremental"
        
        # Update stored metadata
        self.metadata[backup_info.backup_id] = backup_info
        self._save_metadata()
        
        logger.info(f"Created incremental backup: {backup_info.backup_id} (modifications: {modification_count})")
        return backup_info
    
    def restore_from_backup(self, backup_id: str, target_path: Optional[str] = None) -> RestoreResult:
        """
        Restore PDF from specific backup.
        
        Args:
            backup_id: ID of the backup to restore
            target_path: Optional target path, defaults to original location
            
        Returns:
            RestoreResult with restoration details
        """
        errors = []
        
        try:
            if backup_id not in self.metadata:
                errors.append(f"Backup not found: {backup_id}")
                return RestoreResult(False, "", None, errors)
            
            backup_info = self.metadata[backup_id]
            backup_path = Path(backup_info.backup_path)
            
            if not backup_path.exists():
                errors.append(f"Backup file not found: {backup_path}")
                return RestoreResult(False, "", backup_info, errors)
            
            # Determine target path
            if target_path is None:
                target_path = backup_info.original_pdf
            
            target_path = Path(target_path)
            
            # Validate backup integrity before restoration
            if not self._validate_backup_integrity(backup_path):
                errors.append("Backup file appears corrupted")
                return RestoreResult(False, str(target_path), backup_info, errors)
            
            # Create target directory if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Restore file
            shutil.copy2(backup_path, target_path)
            
            logger.info(f"Restored backup {backup_id} to {target_path}")
            return RestoreResult(True, str(target_path), backup_info, errors)
            
        except Exception as e:
            errors.append(f"Restoration failed: {e}")
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return RestoreResult(False, str(target_path) if target_path else "", 
                               self.metadata.get(backup_id), errors)
    
    def list_available_backups(self, pdf_name: Optional[str] = None) -> List[BackupInfo]:
        """
        List all available backups for a PDF.
        
        Args:
            pdf_name: Optional PDF name to filter by
            
        Returns:
            List of BackupInfo sorted by creation time (newest first)
        """
        backups = list(self.metadata.values())
        
        if pdf_name:
            pdf_name = Path(pdf_name).stem
            backups = [b for b in backups if pdf_name in b.backup_id]
        
        # Sort by creation time, newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)
        
        return backups
    
    def cleanup_old_backups(self, days_to_keep: int = 30, keep_important: bool = True) -> CleanupResult:
        """
        Clean up old backup files.
        
        Args:
            days_to_keep: Number of days to keep backups
            keep_important: Whether to preserve backups marked as important
            
        Returns:
            CleanupResult with cleanup statistics
        """
        errors = []
        backups_removed = 0
        space_reclaimed = 0.0
        
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
            
            backups_to_remove = []
            
            for backup_id, backup_info in self.metadata.items():
                if backup_info.created_at < cutoff_date:
                    # Check if marked as important
                    if keep_important and backup_info.metadata.get("important", False):
                        continue
                    
                    backups_to_remove.append(backup_id)
            
            # Remove old backups
            for backup_id in backups_to_remove:
                try:
                    backup_info = self.metadata[backup_id]
                    backup_path = Path(backup_info.backup_path)
                    
                    if backup_path.exists():
                        file_size = backup_path.stat().st_size
                        backup_path.unlink()
                        space_reclaimed += file_size / (1024 * 1024)  # Convert to MB
                    
                    del self.metadata[backup_id]
                    backups_removed += 1
                    
                except Exception as e:
                    errors.append(f"Failed to remove backup {backup_id}: {e}")
            
            # Save updated metadata
            self._save_metadata()
            
            logger.info(f"Cleanup complete: removed {backups_removed} backups, "
                       f"reclaimed {space_reclaimed:.2f} MB")
            
        except Exception as e:
            errors.append(f"Cleanup failed: {e}")
            logger.error(f"Backup cleanup failed: {e}")
        
        return CleanupResult(backups_removed, space_reclaimed, errors)
    
    def _validate_backup_integrity(self, backup_path: Path) -> bool:
        """
        Validate backup file integrity.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if backup appears valid
        """
        try:
            # Basic checks
            if not backup_path.exists():
                return False
            
            if backup_path.stat().st_size == 0:
                return False
            
            # Check PDF header
            with open(backup_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Backup integrity check failed for {backup_path}: {e}")
            return False
    
    def mark_backup_important(self, backup_id: str, important: bool = True) -> bool:
        """
        Mark a backup as important to prevent automatic cleanup.
        
        Args:
            backup_id: ID of backup to mark
            important: Whether to mark as important
            
        Returns:
            True if successfully marked
        """
        try:
            if backup_id not in self.metadata:
                return False
            
            self.metadata[backup_id].metadata["important"] = important
            self._save_metadata()
            
            logger.info(f"Marked backup {backup_id} as {'important' if important else 'normal'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark backup {backup_id}: {e}")
            return False
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the backup system.
        
        Returns:
            Dictionary with backup statistics
        """
        try:
            total_backups = len(self.metadata)
            total_size = sum(info.file_size for info in self.metadata.values())
            
            # Calculate age distribution
            now = datetime.now()
            age_distribution = {"<1_day": 0, "1-7_days": 0, "1-4_weeks": 0, ">4_weeks": 0}
            
            for backup_info in self.metadata.values():
                age_days = (now - backup_info.created_at).days
                if age_days < 1:
                    age_distribution["<1_day"] += 1
                elif age_days <= 7:
                    age_distribution["1-7_days"] += 1
                elif age_days <= 28:
                    age_distribution["1-4_weeks"] += 1
                else:
                    age_distribution[">4_weeks"] += 1
            
            return {
                "total_backups": total_backups,
                "total_size_mb": total_size / (1024 * 1024),
                "backup_directory": str(self.backup_dir),
                "age_distribution": age_distribution,
                "average_size_mb": (total_size / (1024 * 1024) / total_backups) if total_backups > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate backup statistics: {e}")
            return {"error": str(e)}