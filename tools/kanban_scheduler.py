#!/usr/bin/env python3
"""
Kanban Task Scheduler Module

Provides scheduled task management for Kanban boards:
- Release stale claims (claim timeout)
- Promote ready tasks (dependencies satisfied)
- Check timed-out tasks
- Heartbeat claim maintenance

Usage:
    from tools.kanban_scheduler import KanbanScheduler

    scheduler = KanbanScheduler(
        dispatch_interval=60,  # Check interval (seconds)
        claim_timeout=300,     # Claim timeout (seconds)
    )
    scheduler.start()  # Start background scheduler
    # or
    scheduler.run_once()  # Run once
"""

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from common.logging_manager import get_execution_logger
from common.config import get_settings

from tools.kanban_db import (
    KanbanDB,
    claim_release_stale,
    claim_heartbeat,
    claim_get,
    recompute_ready,
    task_update,
    task_get,
    event_add,
)

logger = get_execution_logger("KanbanScheduler")


class KanbanScheduler:
    """
    Kanban Task Scheduler
    
    Main functionalities:
    1. Release stale claims (claim timeout)
    2. Promote ready tasks (dependencies satisfied)
    3. Check timed-out tasks
    4. Heartbeat claim maintenance
    
    Usage:
        scheduler = KanbanScheduler(
            dispatch_interval=60,  # Check interval (seconds)
            claim_timeout=300,     # Claim timeout (seconds)
        )
        scheduler.start()  # Start scheduler
        # or
        scheduler.run_once()  # Run once
    """
    
    def __init__(
        self,
        dispatch_interval: Optional[int] = None,
        claim_timeout: Optional[int] = None,
        db_path: Optional[str] = None,
    ):
        """
        Initialize Kanban scheduler.
        
        Args:
            dispatch_interval: Check interval in seconds (default: 60)
            claim_timeout: Claim timeout in seconds (default: 300)
            db_path: Database path (default: from settings)
        """
        # Load from environment variables or use defaults
        settings = get_settings()
        
        self._dispatch_interval = (
            dispatch_interval
            if dispatch_interval is not None
            else int(os.environ.get("KANBAN_DISPATCH_INTERVAL", "60"))
        )
        self._claim_timeout = (
            claim_timeout
            if claim_timeout is not None
            else int(os.environ.get("KANBAN_CLAIM_TIMEOUT", "300"))
        )
        self._db_path = db_path or os.environ.get("KANBAN_DB_PATH", settings.db_path)
        
        # Ensure database directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Database connection
        self._db: KanbanDB = KanbanDB(self._db_path)
        
        # Background scheduler state
        self._running: bool = False
        self._stop_event: threading.Event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()
    
    @property
    def dispatch_interval(self) -> int:
        """Get dispatch interval in seconds."""
        return self._dispatch_interval
    
    @property
    def claim_timeout(self) -> int:
        """Get claim timeout in seconds."""
        return self._claim_timeout
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return self._db.connect()
    
    def start(self, background: bool = True) -> None:
        """
        Start the scheduler.
        
        Args:
            background: Run in background thread if True, blocking if False
        """
        with self._lock:
            if self._running:
                logger.warning("Scheduler is already running")
                return
            
            self._stop_event.clear()
            self._running = True
            
            if background:
                self._thread = threading.Thread(
                    target=self._run_loop,
                    name="KanbanScheduler",
                    daemon=True,
                )
                self._thread.start()
                logger.info(f"Scheduler started in background (interval={self._dispatch_interval}s)")
            else:
                self._run_loop()
                logger.info("Scheduler finished")
    
    def stop(self, timeout: Optional[float] = None) -> None:
        """
        Stop the scheduler.
        
        Args:
            timeout: Maximum time to wait for thread to stop
        """
        with self._lock:
            if not self._running:
                logger.warning("Scheduler is not running")
                return
            
            self._stop_event.set()
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                logger.info("Scheduler stopped")
            else:
                logger.info("Scheduler stopped (no thread)")
            
            self._thread = None
    
    def _run_loop(self) -> None:
        """Internal run loop for background execution."""
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
            
            # Wait for next interval or stop event
            self._stop_event.wait(timeout=self._dispatch_interval)
    
    def run_once(self) -> Dict[str, Any]:
        """
        Execute one scheduler cycle.
        
        Returns:
            Dict containing:
            - stale_released: Number of stale claims released
            - promoted: Number of tasks promoted to ready
            - timed_out: Number of tasks timed out
            - errors: List of errors encountered
        """
        result: Dict[str, Any] = {
            "stale_released": 0,
            "promoted": 0,
            "timed_out": 0,
            "errors": [],
        }
        
        logger.debug("Scheduler cycle started")
        
        conn = self._get_connection()
        try:
            # Use transaction for consistency
            conn.execute("BEGIN")
            
            # 1. Release stale claims
            try:
                result["stale_released"] = self.release_stale_claims(conn)
                logger.debug(f"Released {result['stale_released']} stale claims")
            except Exception as e:
                error_msg = f"Failed to release stale claims: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            # 2. Recompute ready tasks
            try:
                result["promoted"] = self.recompute_ready(conn)
                logger.debug(f"Promoted {result['promoted']} tasks to ready")
            except Exception as e:
                error_msg = f"Failed to recompute ready tasks: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            # 3. Check timeouts
            try:
                result["timed_out"] = self.check_timeouts(conn)
                logger.debug(f"Timed out {result['timed_out']} tasks")
            except Exception as e:
                error_msg = f"Failed to check timeouts: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Transaction failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        finally:
            self._db.close()
        
        logger.summary(
            f"Scheduler cycle completed: "
            f"released={result['stale_released']}, "
            f"promoted={result['promoted']}, "
            f"timed_out={result['timed_out']}"
        )
        
        return result
    
    def release_stale_claims(self, conn: sqlite3.Connection) -> int:
        """
        Release claims that have exceeded claim_timeout seconds.
        
        Args:
            conn: Database connection
        
        Returns:
            Number of claims released
        """
        released = claim_release_stale(conn, self._claim_timeout)
        
        if released > 0:
            logger.info(f"Released {released} stale claim(s)")
        
        return released
    
    def recompute_ready(self, conn: sqlite3.Connection) -> int:
        """
        Recompute ready status for all tasks.
        
        Tasks in 'todo' status whose all parent tasks are 'done'
        are promoted to 'ready' status.
        
        Args:
            conn: Database connection
        
        Returns:
            Number of tasks promoted
        """
        promoted = recompute_ready(conn)
        
        if promoted > 0:
            logger.info(f"Promoted {promoted} task(s) to ready")
        
        return promoted
    
    def check_timeouts(self, conn: sqlite3.Connection) -> int:
        """
        Check running tasks for timeout.
        
        Tasks with max_runtime_seconds set that exceed this limit
        are marked as 'timed_out' and status changed to 'todo'.
        
        Args:
            conn: Database connection
        
        Returns:
            Number of tasks timed out
        """
        cursor = conn.cursor()
        now = datetime.now()
        timed_out = 0
        
        # Get all running tasks with max_runtime_seconds
        cursor.execute("""
            SELECT id, title, started_at, max_runtime_seconds
            FROM tasks
            WHERE status = 'running'
            AND max_runtime_seconds IS NOT NULL
        """)
        
        for row in cursor.fetchall():
            task_id = row["id"]
            title = row["title"]
            started_at = datetime.fromisoformat(row["started_at"])
            max_runtime = row["max_runtime_seconds"]
            
            # Calculate elapsed time
            elapsed = (now - started_at).total_seconds()
            
            if elapsed > max_runtime:
                # Mark task as timed out
                task_update(conn, task_id, status="todo")
                event_add(
                    conn,
                    task_id,
                    "timed_out",
                    f'{{"elapsed": {elapsed}, "max_runtime": {max_runtime}}}'
                )
                timed_out += 1
                logger.warning(f"Task timed out: {title} (elapsed={elapsed:.0f}s, max={max_runtime}s)")
        
        return timed_out
    
    def heartbeat_claim(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        claimer: str,
    ) -> bool:
        """
        Update heartbeat for a task claim.
        
        Args:
            conn: Database connection
            task_id: Task ID
            claimer: Claimer identifier
        
        Returns:
            True if heartbeat updated, False otherwise
        """
        success = claim_heartbeat(conn, task_id, claimer)
        
        if success:
            logger.debug(f"Heartbeat updated for task {task_id} by {claimer}")
        else:
            logger.warning(f"Failed to update heartbeat for task {task_id}")
        
        return success
    
    def get_claim(self, conn: sqlite3.Connection, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get claim information for a task.
        
        Args:
            conn: Database connection
            task_id: Task ID
        
        Returns:
            Claim info dict or None if not found
        """
        claim = claim_get(conn, task_id)
        
        if claim is None:
            return None
        
        return {
            "task_id": claim.task_id,
            "claimer": claim.claimer,
            "claimed_at": claim.claimed_at,
            "heartbeat_at": claim.heartbeat_at,
        }


# =============================================================================
# Standalone Functions
# =============================================================================

def create_scheduler(
    dispatch_interval: Optional[int] = None,
    claim_timeout: Optional[int] = None,
    db_path: Optional[str] = None,
) -> KanbanScheduler:
    """
    Create a new Kanban scheduler instance.
    
    Args:
        dispatch_interval: Check interval in seconds
        claim_timeout: Claim timeout in seconds
        db_path: Database path
    
    Returns:
        KanbanScheduler instance
    """
    return KanbanScheduler(
        dispatch_interval=dispatch_interval,
        claim_timeout=claim_timeout,
        db_path=db_path,
    )


def run_scheduler_once(
    dispatch_interval: Optional[int] = None,
    claim_timeout: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run scheduler once (convenience function).
    
    Args:
        dispatch_interval: Check interval in seconds
        claim_timeout: Claim timeout in seconds
        db_path: Database path
    
    Returns:
        Scheduler result dict
    """
    scheduler = create_scheduler(
        dispatch_interval=dispatch_interval,
        claim_timeout=claim_timeout,
        db_path=db_path,
    )
    return scheduler.run_once()