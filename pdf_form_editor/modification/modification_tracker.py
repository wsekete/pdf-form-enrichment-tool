#!/usr/bin/env python3
"""
Modification Tracker

Tracks all modifications made to PDF fields with detailed change history,
performance metrics, and audit trails.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field as dataclass_field

from ..utils.logging import get_logger
from .pdf_modifier import FieldModification, ModificationStatus

logger = get_logger(__name__)


@dataclass
class ModificationSession:
    """Complete modification session information."""
    session_id: str
    pdf_path: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_fields: int = 0
    modifications_attempted: int = 0
    modifications_successful: int = 0
    modifications_failed: int = 0
    backup_created: bool = False
    backup_path: str = ""
    processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "pdf_path": self.pdf_path,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_fields": self.total_fields,
            "modifications_attempted": self.modifications_attempted,
            "modifications_successful": self.modifications_successful,
            "modifications_failed": self.modifications_failed,
            "backup_created": self.backup_created,
            "backup_path": self.backup_path,
            "processing_time": self.processing_time,
            "memory_usage_mb": self.memory_usage_mb
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for modification operations."""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_percent: float = 0.0
    success: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "memory_before_mb": self.memory_before_mb,
            "memory_after_mb": self.memory_after_mb,
            "memory_peak_mb": self.memory_peak_mb,
            "cpu_percent": self.cpu_percent,
            "success": self.success,
            "error_message": self.error_message
        }


@dataclass
class ChangeAuditEntry:
    """Audit entry for a single change."""
    timestamp: datetime
    field_id: str
    operation: str  # 'create', 'update', 'delete', 'restore'
    old_value: Any
    new_value: Any
    user_context: str = ""
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "field_id": self.field_id,
            "operation": self.operation,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "user_context": self.user_context,
            "session_id": self.session_id
        }


class ModificationTracker:
    """Track all modifications with detailed history and metrics."""
    
    def __init__(self, tracking_directory: str = "./modification_tracking"):
        """
        Initialize modification tracker.
        
        Args:
            tracking_directory: Directory to store tracking data
        """
        self.tracking_dir = Path(tracking_directory)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[ModificationSession] = None
        self.performance_metrics: List[PerformanceMetrics] = []
        self.audit_trail: List[ChangeAuditEntry] = []
        
        logger.info(f"ModificationTracker initialized with directory: {self.tracking_dir}")
    
    def start_session(self, pdf_path: str, session_id: Optional[str] = None) -> str:
        """
        Start a new modification session.
        
        Args:
            pdf_path: Path to PDF being modified
            session_id: Optional session ID, auto-generated if not provided
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.current_session = ModificationSession(
            session_id=session_id,
            pdf_path=pdf_path,
            start_time=datetime.now()
        )
        
        logger.info(f"Started modification session: {session_id}")
        return session_id
    
    def end_session(self, successful: bool = True) -> Optional[ModificationSession]:
        """
        End the current modification session.
        
        Args:
            successful: Whether the session completed successfully
            
        Returns:
            Completed session information
        """
        if not self.current_session:
            logger.warning("No active session to end")
            return None
        
        self.current_session.end_time = datetime.now()
        self.current_session.processing_time = (
            self.current_session.end_time - self.current_session.start_time
        ).total_seconds()
        
        # Save session data
        self._save_session_data(self.current_session)
        
        completed_session = self.current_session
        self.current_session = None
        
        logger.info(f"Ended modification session: {completed_session.session_id} "
                   f"(duration: {completed_session.processing_time:.2f}s)")
        
        return completed_session
    
    def track_modification(self, modification: FieldModification) -> None:
        """
        Track a field modification.
        
        Args:
            modification: Field modification to track
        """
        if not self.current_session:
            logger.warning("No active session for tracking modification")
            return
        
        # Update session statistics
        self.current_session.modifications_attempted += 1
        
        if modification.status == ModificationStatus.SUCCESS:
            self.current_session.modifications_successful += 1
        elif modification.status == ModificationStatus.FAILED:
            self.current_session.modifications_failed += 1
        
        # Create audit entry
        audit_entry = ChangeAuditEntry(
            timestamp=modification.timestamp or datetime.now(),
            field_id=modification.field_id,
            operation="update",
            old_value=modification.old_name,
            new_value=modification.new_name,
            user_context=f"Field name modification: {modification.preservation_action}",
            session_id=self.current_session.session_id
        )
        
        self.audit_trail.append(audit_entry)
        
        logger.debug(f"Tracked modification: {modification.field_id} "
                    f"({modification.old_name} -> {modification.new_name})")
    
    def track_performance(self, operation_name: str) -> 'PerformanceMonitor':
        """
        Start tracking performance for an operation.
        
        Args:
            operation_name: Name of the operation to track
            
        Returns:
            PerformanceMonitor context manager
        """
        return PerformanceMonitor(self, operation_name)
    
    def add_performance_metric(self, metric: PerformanceMetrics) -> None:
        """
        Add a performance metric.
        
        Args:
            metric: Performance metric to add
        """
        self.performance_metrics.append(metric)
        logger.debug(f"Added performance metric: {metric.operation_name} "
                    f"({metric.duration_seconds:.3f}s)")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session.
        
        Returns:
            Dictionary with session summary
        """
        if not self.current_session:
            return {"status": "no_active_session"}
        
        return {
            "session_id": self.current_session.session_id,
            "pdf_path": self.current_session.pdf_path,
            "duration_seconds": (datetime.now() - self.current_session.start_time).total_seconds(),
            "modifications_attempted": self.current_session.modifications_attempted,
            "modifications_successful": self.current_session.modifications_successful,
            "modifications_failed": self.current_session.modifications_failed,
            "success_rate": (
                self.current_session.modifications_successful / 
                max(1, self.current_session.modifications_attempted)
            ),
            "backup_created": self.current_session.backup_created,
            "active_since": self.current_session.start_time.isoformat()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for current session.
        
        Returns:
            Dictionary with performance summary
        """
        if not self.performance_metrics:
            return {"status": "no_metrics_available"}
        
        total_time = sum(m.duration_seconds for m in self.performance_metrics)
        avg_memory = sum(m.memory_peak_mb for m in self.performance_metrics) / len(self.performance_metrics)
        successful_operations = sum(1 for m in self.performance_metrics if m.success)
        
        operations_by_name = {}
        for metric in self.performance_metrics:
            name = metric.operation_name
            if name not in operations_by_name:
                operations_by_name[name] = []
            operations_by_name[name].append(metric)
        
        operation_summaries = {}
        for name, metrics in operations_by_name.items():
            operation_summaries[name] = {
                "count": len(metrics),
                "total_time": sum(m.duration_seconds for m in metrics),
                "average_time": sum(m.duration_seconds for m in metrics) / len(metrics),
                "success_rate": sum(1 for m in metrics if m.success) / len(metrics),
                "peak_memory": max(m.memory_peak_mb for m in metrics)
            }
        
        return {
            "total_operations": len(self.performance_metrics),
            "successful_operations": successful_operations,
            "total_processing_time": total_time,
            "average_memory_usage_mb": avg_memory,
            "operations_by_type": operation_summaries
        }
    
    def get_audit_trail(self, field_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get audit trail entries.
        
        Args:
            field_id: Optional field ID to filter by
            
        Returns:
            List of audit trail entries
        """
        entries = self.audit_trail
        
        if field_id:
            entries = [entry for entry in entries if entry.field_id == field_id]
        
        return [entry.to_dict() for entry in entries]
    
    def export_tracking_data(self, output_path: str) -> str:
        """
        Export all tracking data to JSON file.
        
        Args:
            output_path: Path for output file
            
        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        
        tracking_data = {
            "export_timestamp": datetime.now().isoformat(),
            "current_session": self.current_session.to_dict() if self.current_session else None,
            "session_summary": self.get_session_summary(),
            "performance_summary": self.get_performance_summary(),
            "performance_metrics": [metric.to_dict() for metric in self.performance_metrics],
            "audit_trail": [entry.to_dict() for entry in self.audit_trail],
            "statistics": {
                "total_audit_entries": len(self.audit_trail),
                "total_performance_metrics": len(self.performance_metrics),
                "unique_fields_modified": len(set(entry.field_id for entry in self.audit_trail))
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Tracking data exported to: {output_path}")
        return str(output_path)
    
    def _save_session_data(self, session: ModificationSession) -> None:
        """
        Save session data to persistent storage.
        
        Args:
            session: Session to save
        """
        try:
            session_file = self.tracking_dir / f"{session.session_id}_session.json"
            session_data = {
                "session_info": session.to_dict(),
                "performance_metrics": [metric.to_dict() for metric in self.performance_metrics],
                "audit_trail": [entry.to_dict() for entry in self.audit_trail]
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Session data saved to: {session_file}")
            
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")
    
    def load_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session data from persistent storage.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            session_file = self.tracking_dir / f"{session_id}_session.json"
            
            if not session_file.exists():
                logger.warning(f"Session file not found: {session_file}")
                return None
            
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            logger.info(f"Session data loaded: {session_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to load session data for {session_id}: {e}")
            return None
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics from all sessions.
        
        Returns:
            Dictionary with overall statistics
        """
        try:
            session_files = list(self.tracking_dir.glob("*_session.json"))
            
            if not session_files:
                return {"total_sessions": 0}
            
            total_sessions = len(session_files)
            total_modifications = 0
            successful_modifications = 0
            total_processing_time = 0.0
            
            for session_file in session_files:
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    session_info = data.get("session_info", {})
                    total_modifications += session_info.get("modifications_attempted", 0)
                    successful_modifications += session_info.get("modifications_successful", 0)
                    total_processing_time += session_info.get("processing_time", 0.0)
                    
                except Exception as e:
                    logger.warning(f"Could not read session file {session_file}: {e}")
            
            return {
                "total_sessions": total_sessions,
                "total_modifications": total_modifications,
                "successful_modifications": successful_modifications,
                "overall_success_rate": successful_modifications / max(1, total_modifications),
                "total_processing_time": total_processing_time,
                "average_processing_time": total_processing_time / max(1, total_sessions)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate session statistics: {e}")
            return {"error": str(e)}


class PerformanceMonitor:
    """Context manager for performance monitoring."""
    
    def __init__(self, tracker: ModificationTracker, operation_name: str):
        """
        Initialize performance monitor.
        
        Args:
            tracker: ModificationTracker instance
            operation_name: Name of operation being monitored
        """
        self.tracker = tracker
        self.metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now()
        )
        
        # Get initial memory usage
        try:
            import psutil
            process = psutil.Process()
            self.metric.memory_before_mb = process.memory_info().rss / 1024 / 1024
            self.metric.memory_peak_mb = self.metric.memory_before_mb
        except ImportError:
            logger.debug("psutil not available, memory tracking disabled")
    
    def __enter__(self):
        """Enter performance monitoring context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit performance monitoring context."""
        self.metric.end_time = datetime.now()
        self.metric.duration_seconds = (
            self.metric.end_time - self.metric.start_time
        ).total_seconds()
        
        # Get final memory usage
        try:
            import psutil
            process = psutil.Process()
            self.metric.memory_after_mb = process.memory_info().rss / 1024 / 1024
            self.metric.memory_peak_mb = max(self.metric.memory_peak_mb, self.metric.memory_after_mb)
            self.metric.cpu_percent = process.cpu_percent()
        except ImportError:
            pass
        
        # Set success status
        self.metric.success = exc_type is None
        if exc_type:
            self.metric.error_message = str(exc_val)
        
        # Add to tracker
        self.tracker.add_performance_metric(self.metric)
    
    def update_peak_memory(self) -> None:
        """Update peak memory usage during operation."""
        try:
            import psutil
            process = psutil.Process()
            current_memory = process.memory_info().rss / 1024 / 1024
            self.metric.memory_peak_mb = max(self.metric.memory_peak_mb, current_memory)
        except ImportError:
            pass