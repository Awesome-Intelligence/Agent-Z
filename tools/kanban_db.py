"""
Kanban SQLite Database Abstraction Layer

Provides database operations for Kanban boards, tasks, and related entities.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Valid task statuses for state machine
VALID_STATUSES = frozenset({
    "triage", "todo", "ready", "running", "blocked", "done", "archived", "timed_out"
})

# State machine transitions
STATUS_TRANSITIONS = {
    "triage": {"todo"},
    "todo": {"ready"},
    "ready": {"running"},
    "running": {"done", "blocked", "timed_out"},
    "blocked": {"ready"},
}

# Status that counts as "active" (not completed/archived)
ACTIVE_STATUSES = frozenset({"triage", "todo", "ready", "running", "blocked"})


@dataclass
class Board:
    """看板数据类"""
    id: str
    name: str
    created_at: str
    tenant: Optional[str] = None


@dataclass
class Task:
    """任务数据类"""
    id: str
    board_id: str
    title: str
    body: Optional[str] = None
    status: str = "todo"
    priority: int = 0
    assignee: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    blocked_reason: Optional[str] = None
    workspace_kind: str = "scratch"
    workspace_path: Optional[str] = None
    max_runtime_seconds: Optional[int] = None
    idempotency_key: Optional[str] = None


@dataclass
class Comment:
    """评论数据类"""
    id: str
    task_id: str
    author: str
    body: str
    created_at: str


@dataclass
class Event:
    """事件数据类"""
    id: int
    task_id: str
    kind: str
    payload: Optional[str] = None
    created_at: str = ""
    run_id: Optional[int] = None


@dataclass
class Run:
    """运行记录数据类"""
    id: int
    task_id: str
    profile: Optional[str] = None
    status: Optional[str] = None
    outcome: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


@dataclass
class Claim:
    """认领数据类"""
    task_id: str
    claimer: str
    claimed_at: str
    heartbeat_at: str


def _row_to_board(row: sqlite3.Row) -> Board:
    """Convert database row to Board dataclass"""
    return Board(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
        tenant=row["tenant"]
    )


def _row_to_task(row: sqlite3.Row) -> Task:
    """Convert database row to Task dataclass"""
    return Task(
        id=row["id"],
        board_id=row["board_id"],
        title=row["title"],
        body=row["body"],
        status=row["status"],
        priority=row["priority"],
        assignee=row["assignee"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        blocked_reason=row["blocked_reason"],
        workspace_kind=row["workspace_kind"],
        workspace_path=row["workspace_path"],
        max_runtime_seconds=row["max_runtime_seconds"],
        idempotency_key=row["idempotency_key"]
    )


def _row_to_comment(row: sqlite3.Row) -> Comment:
    """Convert database row to Comment dataclass"""
    return Comment(
        id=row["id"],
        task_id=row["task_id"],
        author=row["author"],
        body=row["body"],
        created_at=row["created_at"]
    )


def _row_to_event(row: sqlite3.Row) -> Event:
    """Convert database row to Event dataclass"""
    return Event(
        id=row["id"],
        task_id=row["task_id"],
        kind=row["kind"],
        payload=row["payload"],
        created_at=row["created_at"],
        run_id=row["run_id"]
    )


def _row_to_run(row: sqlite3.Row) -> Run:
    """Convert database row to Run dataclass"""
    return Run(
        id=row["id"],
        task_id=row["task_id"],
        profile=row["profile"],
        status=row["status"],
        outcome=row["outcome"],
        summary=row["summary"],
        error=row["error"],
        metadata=row["metadata"],
        started_at=row["started_at"],
        ended_at=row["ended_at"]
    )


def _row_to_claim(row: sqlite3.Row) -> Claim:
    """Convert database row to Claim dataclass"""
    return Claim(
        task_id=row["task_id"],
        claimer=row["claimer"],
        claimed_at=row["claimed_at"],
        heartbeat_at=row["heartbeat_at"]
    )


class KanbanDB:
    """Kanban SQLite Database Abstraction Layer"""

    def __init__(self, db_path: str | Path):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def init_schema(self) -> None:
        """Create all database tables"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # boards table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS boards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tenant TEXT
                )
            """)

            # tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    board_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT,
                    status TEXT DEFAULT 'todo',
                    priority INTEGER DEFAULT 0,
                    assignee TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    blocked_reason TEXT,
                    workspace_kind TEXT DEFAULT 'scratch',
                    workspace_path TEXT,
                    max_runtime_seconds INTEGER,
                    idempotency_key TEXT UNIQUE,
                    FOREIGN KEY (board_id) REFERENCES boards(id)
                )
            """)

            # task_dependencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    PRIMARY KEY (parent_id, child_id),
                    FOREIGN KEY (parent_id) REFERENCES tasks(id),
                    FOREIGN KEY (child_id) REFERENCES tasks(id)
                )
            """)

            # comments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT,
                    created_at TEXT NOT NULL,
                    run_id INTEGER,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # task_runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    profile TEXT,
                    status TEXT,
                    outcome TEXT,
                    summary TEXT,
                    error TEXT,
                    metadata TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # task_claims table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_claims (
                    task_id TEXT PRIMARY KEY,
                    claimer TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            conn.commit()
        finally:
            self.close()

    def connect(self) -> sqlite3.Connection:
        """
        Get database connection
        
        Returns:
            sqlite3.Connection: Database connection
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# =============================================================================
# Board Management
# =============================================================================

def board_create(conn: sqlite3.Connection, name: str, tenant: Optional[str] = None) -> Board:
    """
    Create a new board
    
    Args:
        conn: Database connection
        name: Board name
        tenant: Optional tenant identifier
        
    Returns:
        Board: Created board
    """
    board = Board(
        id=str(uuid.uuid4()),
        name=name,
        created_at=datetime.now().isoformat(),
        tenant=tenant
    )
    
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO boards (id, name, created_at, tenant) VALUES (?, ?, ?, ?)",
        (board.id, board.name, board.created_at, board.tenant)
    )
    
    return board


def board_get(conn: sqlite3.Connection, board_id: str) -> Optional[Board]:
    """
    Get board by ID
    
    Args:
        conn: Database connection
        board_id: Board ID
        
    Returns:
        Optional[Board]: Board if found, None otherwise
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards WHERE id = ?", (board_id,))
    row = cursor.fetchone()
    
    if row is None:
        return None
    return _row_to_board(row)


def board_list(conn: sqlite3.Connection) -> list[Board]:
    """
    List all boards
    
    Args:
        conn: Database connection
        
    Returns:
        list[Board]: List of all boards
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    return [_row_to_board(row) for row in rows]


def board_delete(conn: sqlite3.Connection, board_id: str) -> bool:
    """
    Delete a board and all its tasks
    
    Args:
        conn: Database connection
        board_id: Board ID
        
    Returns:
        bool: True if deleted, False if not found
    """
    cursor = conn.cursor()
    
    # Delete task dependencies first
    cursor.execute("""
        DELETE FROM task_dependencies 
        WHERE parent_id IN (SELECT id FROM tasks WHERE board_id = ?)
        OR child_id IN (SELECT id FROM tasks WHERE board_id = ?)
    """, (board_id, board_id))
    
    # Delete comments, events, runs, claims for tasks in board
    cursor.execute("SELECT id FROM tasks WHERE board_id = ?", (board_id,))
    task_ids = [row["id"] for row in cursor.fetchall()]
    
    for task_id in task_ids:
        cursor.execute("DELETE FROM comments WHERE task_id = ?", (task_id,))
        cursor.execute("DELETE FROM events WHERE task_id = ?", (task_id,))
        cursor.execute("DELETE FROM task_runs WHERE task_id = ?", (task_id,))
        cursor.execute("DELETE FROM task_claims WHERE task_id = ?", (task_id,))
    
    # Delete tasks
    cursor.execute("DELETE FROM tasks WHERE board_id = ?", (board_id,))
    
    # Delete board
    cursor.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    
    return cursor.rowcount > 0


# =============================================================================
# Task Management
# =============================================================================

def task_create(
    conn: sqlite3.Connection,
    board_id: str,
    title: str,
    body: Optional[str] = None,
    status: str = "todo",
    priority: int = 0,
    assignee: Optional[str] = None,
    created_by: Optional[str] = None,
    workspace_kind: str = "scratch",
    workspace_path: Optional[str] = None,
    max_runtime_seconds: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    initial_status: str = "running",
    skills: Optional[list[str]] = None,
    tenant: Optional[str] = None,
    session_id: Optional[str] = None
) -> Task | str:
    """
    Create a new task
    
    If idempotency_key is provided and a task with that key exists,
    returns the existing task ID instead of creating a new one.
    
    Args:
        conn: Database connection
        board_id: Board ID
        title: Task title
        body: Task body/description
        status: Task status
        priority: Task priority
        assignee: Assignee identifier
        created_by: Creator identifier
        workspace_kind: Workspace kind
        workspace_path: Workspace path
        max_runtime_seconds: Maximum runtime
        idempotency_key: Idempotency key for deduplication
        initial_status: Initial status (default: running)
        skills: Task skills
        tenant: Tenant identifier
        session_id: Session identifier
        
    Returns:
        Task | str: Created task or existing task ID if idempotent
    """
    now = datetime.now().isoformat()
    
    # Check for existing task with idempotency_key
    if idempotency_key:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM tasks WHERE idempotency_key = ?",
            (idempotency_key,)
        )
        row = cursor.fetchone()
        if row:
            return row["id"]
    
    task = Task(
        id=str(uuid.uuid4()),
        board_id=board_id,
        title=title,
        body=body,
        status=status,
        priority=priority,
        assignee=assignee,
        created_by=created_by,
        created_at=now,
        updated_at=now,
        workspace_kind=workspace_kind,
        workspace_path=workspace_path,
        max_runtime_seconds=max_runtime_seconds,
        idempotency_key=idempotency_key
    )
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (
            id, board_id, title, body, status, priority, assignee, created_by,
            created_at, updated_at, workspace_kind, workspace_path,
            max_runtime_seconds, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task.id, task.board_id, task.title, task.body, task.status,
        task.priority, task.assignee, task.created_by, task.created_at,
        task.updated_at, task.workspace_kind, task.workspace_path,
        task.max_runtime_seconds, task.idempotency_key
    ))
    
    return task.id


def task_get(conn: sqlite3.Connection, task_id: str) -> Optional[Task]:
    """
    Get task by ID
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        Optional[Task]: Task if found, None otherwise
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    if row is None:
        return None
    return _row_to_task(row)


def task_list(
    conn: sqlite3.Connection,
    board_id: Optional[str] = None,
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    tenant: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 50
) -> list[Task]:
    """
    List tasks with optional filters
    
    Args:
        conn: Database connection
        board_id: Filter by board ID
        assignee: Filter by assignee
        status: Filter by status
        tenant: Filter by tenant
        include_archived: Include archived tasks
        limit: Maximum number of tasks to return
        
    Returns:
        list[Task]: List of tasks
    """
    cursor = conn.cursor()
    
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list[Any] = []
    
    if board_id:
        query += " AND board_id = ?"
        params.append(board_id)
    
    if assignee:
        query += " AND assignee = ?"
        params.append(assignee)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if not include_archived:
        query += " AND status != 'archived'"
    
    query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    return [_row_to_task(row) for row in rows]


def task_update(conn: sqlite3.Connection, task_id: str, **kwargs: Any) -> Optional[Task]:
    """
    Update task fields
    
    Args:
        conn: Database connection
        task_id: Task ID
        **kwargs: Fields to update
        
    Returns:
        Optional[Task]: Updated task if found, None otherwise
    """
    valid_fields = {
        "title", "body", "status", "priority", "assignee",
        "started_at", "completed_at", "blocked_reason",
        "workspace_kind", "workspace_path", "max_runtime_seconds"
    }
    
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}
    
    if not updates:
        return task_get(conn, task_id)
    
    updates["updated_at"] = datetime.now().isoformat()
    
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [task_id]
    
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE tasks SET {set_clause} WHERE id = ?",
        values
    )
    
    if cursor.rowcount == 0:
        return None
    
    return task_get(conn, task_id)


def task_delete(conn: sqlite3.Connection, task_id: str) -> bool:
    """
    Delete a task and related data
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        bool: True if deleted, False if not found
    """
    cursor = conn.cursor()
    
    # Delete dependencies
    cursor.execute(
        "DELETE FROM task_dependencies WHERE parent_id = ? OR child_id = ?",
        (task_id, task_id)
    )
    
    # Delete related data
    cursor.execute("DELETE FROM comments WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM events WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM task_runs WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM task_claims WHERE task_id = ?", (task_id,))
    
    # Delete task
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    
    return cursor.rowcount > 0


def task_find_by_idempotency_key(conn: sqlite3.Connection, key: str) -> Optional[Task]:
    """
    Find task by idempotency key
    
    Args:
        conn: Database connection
        key: Idempotency key
        
    Returns:
        Optional[Task]: Task if found, None otherwise
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM tasks WHERE idempotency_key = ?",
        (key,)
    )
    row = cursor.fetchone()
    
    if row is None:
        return None
    return _row_to_task(row)


# =============================================================================
# Task State Transitions
# =============================================================================

def task_start(conn: sqlite3.Connection, task_id: str) -> Optional[Task]:
    """
    Start a task (transition to running)
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        Optional[Task]: Updated task if found
        
    Raises:
        ValueError: If transition is not valid
    """
    task = task_get(conn, task_id)
    if task is None:
        return None
    
    # Check if task.status can transition to 'running'
    # Find all source statuses that can transition to 'running'
    can_start = any('running' in targets for source, targets in STATUS_TRANSITIONS.items() if source != 'running')
    if task.status not in [s for s, t in STATUS_TRANSITIONS.items() if 'running' in t]:
        raise ValueError(f"Cannot start task from status '{task.status}'")
    
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = 'running', started_at = ?, updated_at = ?
        WHERE id = ?
    """, (now, now, task_id))
    
    return task_get(conn, task_id)


def task_complete(
    conn: sqlite3.Connection,
    task_id: str,
    result: Optional[str] = None,
    summary: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    created_cards: Optional[list[str]] = None,
    artifacts: Optional[list[str]] = None,
    expected_run_id: Optional[int] = None
) -> Optional[Task]:
    """
    Complete a task (transition to done)
    
    Also checks if child tasks can be promoted to ready.
    
    Args:
        conn: Database connection
        task_id: Task ID
        result: Task result
        summary: Task summary
        metadata: Task metadata
        created_cards: Created card IDs
        artifacts: Artifact paths
        expected_run_id: Expected run ID
        
    Returns:
        Optional[Task]: Updated task if found
        
    Raises:
        ValueError: If transition is not valid
    """
    task = task_get(conn, task_id)
    if task is None:
        return None
    
    if task.status != "running":
        raise ValueError(f"Cannot complete task from status '{task.status}'")
    
    now = datetime.now().isoformat()
    metadata_json = json.dumps(metadata) if metadata else None
    artifacts_json = json.dumps(artifacts) if artifacts else None
    created_cards_json = json.dumps(created_cards) if created_cards else None
    
    payload = {
        "result": result,
        "summary": summary,
        "metadata": metadata,
        "artifacts": artifacts,
        "created_cards": created_cards
    }
    
    # Update task status
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = 'done', completed_at = ?, updated_at = ?
        WHERE id = ?
    """, (now, now, task_id))
    
    # Add completion event
    event_add(conn, task_id, "completed", json.dumps(payload), expected_run_id)
    
    # Check child tasks for promotion to ready
    _promote_child_tasks(conn, task_id)
    
    return task_get(conn, task_id)


def task_block(
    conn: sqlite3.Connection,
    task_id: str,
    reason: str,
    expected_run_id: Optional[int] = None
) -> Optional[Task]:
    """
    Block a task (transition to blocked)
    
    Args:
        conn: Database connection
        task_id: Task ID
        reason: Blocking reason
        expected_run_id: Expected run ID
        
    Returns:
        Optional[Task]: Updated task if found
        
    Raises:
        ValueError: If transition is not valid
    """
    task = task_get(conn, task_id)
    if task is None:
        return None
    
    if task.status != "running":
        raise ValueError(f"Cannot block task from status '{task.status}'")
    
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = 'blocked', blocked_reason = ?, updated_at = ?
        WHERE id = ?
    """, (reason, now, task_id))
    
    event_add(conn, task_id, "blocked", json.dumps({"reason": reason}), expected_run_id)
    
    return task_get(conn, task_id)


def task_unblock(conn: sqlite3.Connection, task_id: str) -> Optional[Task]:
    """
    Unblock a task (transition to ready)
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        Optional[Task]: Updated task if found
        
    Raises:
        ValueError: If transition is not valid
    """
    task = task_get(conn, task_id)
    if task is None:
        return None
    
    if task.status != "blocked":
        raise ValueError(f"Cannot unblock task from status '{task.status}'")
    
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = 'ready', blocked_reason = NULL, updated_at = ?
        WHERE id = ?
    """, (now, task_id))
    
    event_add(conn, task_id, "unblocked")
    
    return task_get(conn, task_id)


def task_archive(conn: sqlite3.Connection, task_id: str) -> Optional[Task]:
    """
    Archive a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        Optional[Task]: Updated task if found
    """
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = 'archived', updated_at = ?
        WHERE id = ?
    """, (now, task_id))
    
    if cursor.rowcount == 0:
        return None
    
    return task_get(conn, task_id)


def _promote_child_tasks(conn: sqlite3.Connection, parent_id: str) -> None:
    """
    Promote child tasks to ready if all their dependencies are satisfied
    
    Args:
        conn: Database connection
        parent_id: Completed parent task ID
    """
    cursor = conn.cursor()
    
    # Get all child task IDs
    cursor.execute("""
        SELECT child_id FROM task_dependencies WHERE parent_id = ?
    """, (parent_id,))
    child_ids = [row["child_id"] for row in cursor.fetchall()]
    
    for child_id in child_ids:
        child = task_get(conn, child_id)
        if child is None or child.status != "todo":
            continue
        
        # Check if all parent tasks are done
        cursor.execute("""
            SELECT parent_id FROM task_dependencies WHERE child_id = ?
        """, (child_id,))
        parent_ids = [row["parent_id"] for row in cursor.fetchall()]
        
        if not parent_ids:
            continue
        
        placeholders = ",".join(["?"] * len(parent_ids))
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM tasks 
            WHERE id IN ({placeholders}) AND status = 'done'
        """, parent_ids)
        
        done_count = cursor.fetchone()["count"]
        
        if done_count == len(parent_ids):
            # All dependencies satisfied, promote to ready
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE tasks SET status = 'ready', updated_at = ? WHERE id = ?
            """, (now, child_id))
            event_add(conn, child_id, "promoted", '{"reason": "dependencies_satisfied"}')


# =============================================================================
# Dependency Management
# =============================================================================

def dep_link(conn: sqlite3.Connection, parent_id: str, child_id: str) -> bool:
    """
    Link parent task to child task dependency
    
    Args:
        conn: Database connection
        parent_id: Parent task ID
        child_id: Child task ID
        
    Returns:
        bool: True if linked, False if already linked
        
    Raises:
        ValueError: If cycle would be created
    """
    if dep_check_cycle(conn, parent_id, child_id):
        raise ValueError(f"Linking {parent_id} -> {child_id} would create a cycle")
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO task_dependencies (parent_id, child_id) VALUES (?, ?)
        """, (parent_id, child_id))
        return True
    except sqlite3.IntegrityError:
        return False


def dep_unlink(conn: sqlite3.Connection, parent_id: str, child_id: str) -> bool:
    """
    Remove dependency link between tasks
    
    Args:
        conn: Database connection
        parent_id: Parent task ID
        child_id: Child task ID
        
    Returns:
        bool: True if unlinked, False if not found
    """
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM task_dependencies WHERE parent_id = ? AND child_id = ?
    """, (parent_id, child_id))
    
    return cursor.rowcount > 0


def dep_parent_ids(conn: sqlite3.Connection, task_id: str) -> list[str]:
    """
    Get parent task IDs for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        list[str]: List of parent task IDs
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT parent_id FROM task_dependencies WHERE child_id = ?
    """, (task_id,))
    
    return [row["parent_id"] for row in cursor.fetchall()]


def dep_child_ids(conn: sqlite3.Connection, task_id: str) -> list[str]:
    """
    Get child task IDs for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        list[str]: List of child task IDs
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT child_id FROM task_dependencies WHERE parent_id = ?
    """, (task_id,))
    
    return [row["child_id"] for row in cursor.fetchall()]


def dep_check_cycle(conn: sqlite3.Connection, parent_id: str, child_id: str) -> bool:
    """
    Check if adding a dependency would create a cycle
    
    Args:
        conn: Database connection
        parent_id: Parent task ID
        child_id: Child task ID
        
    Returns:
        bool: True if cycle would be created
    """
    # If parent_id equals child_id, it's a self-loop
    if parent_id == child_id:
        return True
    
    # Check if we can reach parent_id from child_id
    # If yes, adding parent_id -> child_id would create a cycle
    visited: set[str] = set()
    to_visit = [child_id]
    
    while to_visit:
        current = to_visit.pop()
        if current == parent_id:
            return True
        
        if current in visited:
            continue
        visited.add(current)
        
        # Add children to visit queue
        cursor = conn.cursor()
        cursor.execute("""
            SELECT child_id FROM task_dependencies WHERE parent_id = ?
        """, (current,))
        
        for row in cursor.fetchall():
            if row["child_id"] not in visited:
                to_visit.append(row["child_id"])
    
    return False


# =============================================================================
# Comments and Events
# =============================================================================

def comment_add(conn: sqlite3.Connection, task_id: str, author: str, body: str) -> Comment:
    """
    Add a comment to a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        author: Comment author
        body: Comment body
        
    Returns:
        Comment: Created comment
    """
    comment = Comment(
        id=str(uuid.uuid4()),
        task_id=task_id,
        author=author,
        body=body,
        created_at=datetime.now().isoformat()
    )
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO comments (id, task_id, author, body, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (comment.id, comment.task_id, comment.author, comment.body, comment.created_at))
    
    return comment


def comment_list(conn: sqlite3.Connection, task_id: str) -> list[Comment]:
    """
    List comments for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        list[Comment]: List of comments
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM comments WHERE task_id = ? ORDER BY created_at ASC
    """, (task_id,))
    
    return [_row_to_comment(row) for row in cursor.fetchall()]


def event_add(
    conn: sqlite3.Connection,
    task_id: str,
    kind: str,
    payload: Optional[str] = None,
    run_id: Optional[int] = None
) -> Event:
    """
    Add an event to a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        kind: Event kind
        payload: Event payload (JSON string)
        run_id: Associated run ID
        
    Returns:
        Event: Created event
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (task_id, kind, payload, created_at, run_id)
        VALUES (?, ?, ?, ?, ?)
    """, (task_id, kind, payload, datetime.now().isoformat(), run_id))
    
    event = Event(
        id=cursor.lastrowid,
        task_id=task_id,
        kind=kind,
        payload=payload,
        created_at=datetime.now().isoformat(),
        run_id=run_id
    )
    
    return event


def event_list(conn: sqlite3.Connection, task_id: str, limit: int = 50) -> list[Event]:
    """
    List events for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        limit: Maximum number of events
        
    Returns:
        list[Event]: List of events
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM events WHERE task_id = ? 
        ORDER BY created_at DESC LIMIT ?
    """, (task_id, limit))
    
    return [_row_to_event(row) for row in cursor.fetchall()]


# =============================================================================
# Task Run Records
# =============================================================================

def run_start(conn: sqlite3.Connection, task_id: str, profile: Optional[str] = None) -> Run:
    """
    Start a run record for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        profile: Profile identifier
        
    Returns:
        Run: Created run record
    """
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO task_runs (task_id, profile, status, started_at)
        VALUES (?, ?, 'running', ?)
    """, (task_id, profile, now))
    
    run = Run(
        id=cursor.lastrowid,
        task_id=task_id,
        profile=profile,
        status="running",
        started_at=now
    )
    
    return run


def run_end(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    outcome: Optional[str] = None,
    summary: Optional[str] = None,
    error: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None
) -> Optional[Run]:
    """
    End a run record
    
    Args:
        conn: Database connection
        run_id: Run ID
        status: Run status
        outcome: Run outcome
        summary: Run summary
        error: Error message
        metadata: Run metadata
        
    Returns:
        Optional[Run]: Updated run record
    """
    now = datetime.now().isoformat()
    metadata_json = json.dumps(metadata) if metadata else None
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE task_runs 
        SET status = ?, outcome = ?, summary = ?, error = ?, 
            metadata = ?, ended_at = ?
        WHERE id = ?
    """, (status, outcome, summary, error, metadata_json, now, run_id))
    
    if cursor.rowcount == 0:
        return None
    
    return run_get(conn, run_id)


def run_get(conn: sqlite3.Connection, run_id: int) -> Optional[Run]:
    """
    Get a run record by ID
    
    Args:
        conn: Database connection
        run_id: Run ID
        
    Returns:
        Optional[Run]: Run record if found
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM task_runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    
    if row is None:
        return None
    return _row_to_run(row)


def run_latest(conn: sqlite3.Connection, task_id: str) -> Optional[Run]:
    """
    Get the latest run record for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        Optional[Run]: Latest run record
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM task_runs WHERE task_id = ? 
        ORDER BY started_at DESC LIMIT 1
    """, (task_id,))
    row = cursor.fetchone()
    
    if row is None:
        return None
    return _row_to_run(row)


def run_list(conn: sqlite3.Connection, task_id: str) -> list[Run]:
    """
    List all run records for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        list[Run]: List of run records
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM task_runs WHERE task_id = ? ORDER BY started_at DESC
    """, (task_id,))
    
    return [_row_to_run(row) for row in cursor.fetchall()]


# =============================================================================
# Scheduler Support
# =============================================================================

def claim_task(conn: sqlite3.Connection, task_id: str, claimer: str) -> Claim:
    """
    Claim a task for execution
    
    Args:
        conn: Database connection
        task_id: Task ID
        claimer: Claimer identifier
        
    Returns:
        Claim: Created claim
        
    Raises:
        sqlite3.IntegrityError: If task is already claimed
    """
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO task_claims (task_id, claimer, claimed_at, heartbeat_at)
        VALUES (?, ?, ?, ?)
    """, (task_id, claimer, now, now))
    
    return Claim(
        task_id=task_id,
        claimer=claimer,
        claimed_at=now,
        heartbeat_at=now
    )


def claim_release(conn: sqlite3.Connection, task_id: str) -> bool:
    """
    Release a task claim
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        bool: True if released
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM task_claims WHERE task_id = ?", (task_id,))
    return cursor.rowcount > 0


def claim_release_stale(conn: sqlite3.Connection, max_age_seconds: int) -> int:
    """
    Release stale task claims
    
    Args:
        conn: Database connection
        max_age_seconds: Maximum age in seconds
        
    Returns:
        int: Number of claims released
    """
    from datetime import timedelta
    
    cutoff = (datetime.now() - timedelta(seconds=max_age_seconds)).isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM task_claims WHERE heartbeat_at < ?
    """, (cutoff,))
    
    return cursor.rowcount


def claim_heartbeat(conn: sqlite3.Connection, task_id: str, claimer: str) -> bool:
    """
    Update heartbeat for a task claim
    
    Args:
        conn: Database connection
        task_id: Task ID
        claimer: Claimer identifier
        
    Returns:
        bool: True if heartbeat updated
    """
    now = datetime.now().isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE task_claims 
        SET heartbeat_at = ?
        WHERE task_id = ? AND claimer = ?
    """, (now, task_id, claimer))
    
    return cursor.rowcount > 0


def claim_get(conn: sqlite3.Connection, task_id: str) -> Optional[Claim]:
    """
    Get claim information for a task
    
    Args:
        conn: Database connection
        task_id: Task ID
        
    Returns:
        Optional[Claim]: Claim if found
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM task_claims WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    
    if row is None:
        return None
    return _row_to_claim(row)


# =============================================================================
# Recompute Ready Status
# =============================================================================

def recompute_ready(conn: sqlite3.Connection) -> int:
    """
    Recompute ready status for all tasks
    
    Tasks in 'todo' status whose all parent tasks are 'done'
    are promoted to 'ready' status.
    
    Args:
        conn: Database connection
        
    Returns:
        int: Number of tasks promoted
    """
    cursor = conn.cursor()
    
    # Get all todo tasks
    cursor.execute("SELECT * FROM tasks WHERE status = 'todo'")
    todo_tasks = [_row_to_task(row) for row in cursor.fetchall()]
    
    promoted = 0
    now = datetime.now().isoformat()
    
    for task in todo_tasks:
        # Get parent IDs
        parent_ids = dep_parent_ids(conn, task.id)
        
        if not parent_ids:
            continue
        
        # Check if all parents are done
        placeholders = ",".join(["?"] * len(parent_ids))
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM tasks 
            WHERE id IN ({placeholders}) AND status = 'done'
        """, parent_ids)
        
        done_count = cursor.fetchone()["count"]
        
        if done_count == len(parent_ids):
            cursor.execute("""
                UPDATE tasks SET status = 'ready', updated_at = ? WHERE id = ?
            """, (now, task.id))
            event_add(conn, task.id, "promoted", '{"reason": "recomputed"}')
            promoted += 1
    
    return promoted