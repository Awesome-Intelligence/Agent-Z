#!/usr/bin/env python3
"""
Kanban Tool Module

Provides kanban/task management functionality based on SQLite database:
- Board creation and management
- Task CRUD operations
- Task state transitions (triage → todo → ready → running → done)
- Dependencies and comments
- Full Hermes-style API support

Based on Hermes Agent's kanban_tools.py and kanban_db.py implementation.

Usage:
    from tools.kanban_tool import kanban_create, kanban_show, kanban_list
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger
from tools.registry import registry

from tools.kanban_db import (
    KanbanDB,
    board_create,
    board_delete,
    board_get,
    board_list,
    task_create,
    task_get,
    task_list,
    task_update,
    task_delete,
    task_complete,
    task_block,
    task_unblock,
    dep_link,
    dep_unlink,
    dep_parent_ids,
    dep_child_ids,
    comment_add,
    comment_list,
    event_list,
    run_list,
)

logger = get_execution_logger("KanbanTool")

# Database path
DB_PATH = Path.home() / ".handsome_agent" / "kanban.db"


class KanbanManager:
    """看板管理器，使用 SQLite 数据库"""

    def __init__(self):
        self._db = KanbanDB(DB_PATH)
        self._db.init_schema()
        # 确保默认看板存在
        self._ensure_default_board()

    def _ensure_default_board(self) -> None:
        """确保存在默认看板"""
        conn = self._db.connect()
        try:
            boards = board_list(conn)
            if not boards:
                board_create(conn, "Default Board", tenant="default")
                logger.info("Created default board")
        finally:
            self._db.close()

    @property
    def db(self) -> KanbanDB:
        """获取数据库实例"""
        return self._db

    def get_default_board_id(self) -> Optional[str]:
        """获取默认看板ID"""
        conn = self._db.connect()
        try:
            boards = board_list(conn)
            if boards:
                return boards[0].id
            return None
        finally:
            self._db.close()

    def create_board(self, name: str, tenant: Optional[str] = None) -> str:
        """创建看板"""
        conn = self._db.connect()
        try:
            board = board_create(conn, name, tenant)
            conn.commit()  # 提交事务
            logger.info(f"Created board: {name} ({board.id})")
            return board.id
        finally:
            self._db.close()

    def delete_board(self, board_id: str) -> bool:
        """删除看板"""
        conn = self._db.connect()
        try:
            result = board_delete(conn, board_id)
            conn.commit()  # 提交事务
            logger.info(f"Deleted board: {board_id}")
            return result
        finally:
            self._db.close()

    def get_board(self, board_id: str) -> Optional[Any]:
        """获取看板"""
        conn = self._db.connect()
        try:
            return board_get(conn, board_id)
        finally:
            self._db.close()

    def list_boards(self) -> List[Dict[str, Any]]:
        """列出所有看板"""
        conn = self._db.connect()
        try:
            boards = board_list(conn)
            result = []
            for board in boards:
                # 获取任务数量
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM tasks WHERE board_id = ?",
                    (board.id,)
                )
                task_count = cursor.fetchone()["count"]
                result.append({
                    "id": board.id,
                    "name": board.name,
                    "created_at": board.created_at,
                    "tenant": board.tenant,
                    "task_count": task_count,
                })
            return result
        finally:
            self._db.close()

    def create_task(
        self,
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
        skills: Optional[List[str]] = None,
        tenant: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """创建任务"""
        conn = self._db.connect()
        try:
            result = task_create(
                conn=conn,
                board_id=board_id,
                title=title,
                body=body,
                status=status,
                priority=priority,
                assignee=assignee,
                created_by=created_by,
                workspace_kind=workspace_kind,
                workspace_path=workspace_path,
                max_runtime_seconds=max_runtime_seconds,
                idempotency_key=idempotency_key,
                initial_status=initial_status,
                skills=skills,
                tenant=tenant,
                session_id=session_id,
            )
            conn.commit()  # 提交事务
            logger.info(f"Created task: {title} ({result})")
            return result if isinstance(result, str) else result.id
        finally:
            self._db.close()

    def get_task(self, task_id: str) -> Optional[Any]:
        """获取任务"""
        conn = self._db.connect()
        try:
            return task_get(conn, task_id)
        finally:
            self._db.close()

    def list_tasks(
        self,
        board_id: Optional[str] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        tenant: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> List[Any]:
        """列出任务"""
        conn = self._db.connect()
        try:
            return task_list(
                conn,
                board_id=board_id,
                assignee=assignee,
                status=status,
                tenant=tenant,
                include_archived=include_archived,
                limit=limit,
            )
        finally:
            self._db.close()

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs,
    ) -> Optional[Any]:
        """更新任务"""
        conn = self._db.connect()
        try:
            updates = {}
            if title is not None:
                updates["title"] = title
            if body is not None:
                updates["body"] = body
            if priority is not None:
                updates["priority"] = priority
            if assignee is not None:
                updates["assignee"] = assignee
            if status is not None:
                updates["status"] = status
            updates.update(kwargs)

            result = task_update(conn, task_id, **updates)
            conn.commit()  # 提交事务
            logger.info(f"Updated task: {task_id}")
            return result
        finally:
            self._db.close()

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        conn = self._db.connect()
        try:
            result = task_delete(conn, task_id)
            conn.commit()  # 提交事务
            logger.info(f"Deleted task: {task_id}")
            return result
        finally:
            self._db.close()

    def complete_task(
        self,
        task_id: str,
        result: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_cards: Optional[List[str]] = None,
        artifacts: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """完成任务"""
        conn = self._db.connect()
        try:
            result_task = task_complete(
                conn=conn,
                task_id=task_id,
                result=result,
                summary=summary,
                metadata=metadata,
                created_cards=created_cards,
                artifacts=artifacts,
            )
            conn.commit()  # 提交事务
            logger.info(f"Completed task: {task_id}")
            return result_task
        finally:
            self._db.close()

    def block_task(self, task_id: str, reason: str) -> Optional[Any]:
        """阻塞任务"""
        conn = self._db.connect()
        try:
            result = task_block(conn, task_id, reason)
            conn.commit()  # 提交事务
            logger.info(f"Blocked task: {task_id} - {reason}")
            return result
        finally:
            self._db.close()

    def unblock_task(self, task_id: str) -> Optional[Any]:
        """解阻塞任务"""
        conn = self._db.connect()
        try:
            result = task_unblock(conn, task_id)
            conn.commit()  # 提交事务
            logger.info(f"Unblocked task: {task_id}")
            return result
        finally:
            self._db.close()

    def link_tasks(self, parent_id: str, child_id: str) -> bool:
        """链接任务依赖"""
        conn = self._db.connect()
        try:
            result = dep_link(conn, parent_id, child_id)
            conn.commit()  # 提交事务
            logger.info(f"Linked tasks: {parent_id} -> {child_id}")
            return result
        finally:
            self._db.close()

    def unlink_tasks(self, parent_id: str, child_id: str) -> bool:
        """取消链接任务依赖"""
        conn = self._db.connect()
        try:
            result = dep_unlink(conn, parent_id, child_id)
            conn.commit()  # 提交事务
            logger.info(f"Unlinked tasks: {parent_id} -> {child_id}")
            return result
        finally:
            self._db.close()

    def get_dependencies(self, task_id: str) -> Dict[str, List[str]]:
        """获取任务依赖"""
        conn = self._db.connect()
        try:
            return {
                "parents": dep_parent_ids(conn, task_id),
                "children": dep_child_ids(conn, task_id),
            }
        finally:
            self._db.close()

    def add_comment(self, task_id: str, author: str, body: str) -> Any:
        """添加评论"""
        conn = self._db.connect()
        try:
            comment = comment_add(conn, task_id, author, body)
            conn.commit()  # 提交事务
            logger.info(f"Added comment to task: {task_id}")
            return comment
        finally:
            self._db.close()

    def get_comments(self, task_id: str) -> List[Any]:
        """获取任务评论"""
        conn = self._db.connect()
        try:
            return comment_list(conn, task_id)
        finally:
            self._db.close()

    def get_events(self, task_id: str, limit: int = 50) -> List[Any]:
        """获取任务事件"""
        conn = self._db.connect()
        try:
            return event_list(conn, task_id, limit)
        finally:
            self._db.close()

    def get_runs(self, task_id: str) -> List[Any]:
        """获取任务运行记录"""
        conn = self._db.connect()
        try:
            return run_list(conn, task_id)
        finally:
            self._db.close()


# 全局管理器实例
_kanban_manager = KanbanManager()


def _get_author() -> str:
    """获取当前用户标识"""
    return os.environ.get("HERMES_PROFILE", "unknown")


def _task_to_dict(task: Any) -> Dict[str, Any]:
    """将任务对象转换为字典"""
    if task is None:
        return {}
    return {
        "id": task.id,
        "board_id": task.board_id,
        "title": task.title,
        "body": task.body,
        "status": task.status,
        "priority": task.priority,
        "assignee": task.assignee,
        "created_by": task.created_by,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "blocked_reason": task.blocked_reason,
        "workspace_kind": task.workspace_kind,
        "workspace_path": task.workspace_path,
        "max_runtime_seconds": task.max_runtime_seconds,
        "idempotency_key": task.idempotency_key,
    }


def _comment_to_dict(comment: Any) -> Dict[str, Any]:
    """将评论对象转换为字典"""
    if comment is None:
        return {}
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "author": comment.author,
        "body": comment.body,
        "created_at": comment.created_at,
    }


def _event_to_dict(event: Any) -> Dict[str, Any]:
    """将事件对象转换为字典"""
    if event is None:
        return {}
    return {
        "id": event.id,
        "task_id": event.task_id,
        "kind": event.kind,
        "payload": event.payload,
        "created_at": event.created_at,
        "run_id": event.run_id,
    }


def _run_to_dict(run: Any) -> Dict[str, Any]:
    """将运行记录转换为字典"""
    if run is None:
        return {}
    return {
        "id": run.id,
        "task_id": run.task_id,
        "profile": run.profile,
        "status": run.status,
        "outcome": run.outcome,
        "summary": run.summary,
        "error": run.error,
        "metadata": run.metadata,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
    }


# =============================================================================
# 保留的工具函数（兼容性）
# =============================================================================

def kanban_create_board(name: str) -> str:
    """
    创建看板。

    Args:
        name: 看板名称

    Returns:
        JSON 格式的结果字符串
    """
    try:
        board_id = _kanban_manager.create_board(name)
        result = {
            "success": True,
            "board_id": board_id,
            "name": name,
            "message": f"看板已创建: {name}",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to create board: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_delete_board(board_id: str) -> str:
    """
    删除看板。

    Args:
        board_id: 看板ID

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.delete_board(board_id)
        if success:
            result = {"success": True, "message": "看板已删除"}
        else:
            result = {"success": False, "error": f"看板不存在: {board_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to delete board: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_list_boards() -> str:
    """
    列出所有看板。

    Returns:
        JSON 格式的结果字符串
    """
    try:
        boards = _kanban_manager.list_boards()
        result = {
            "success": True,
            "boards": boards,
            "total": len(boards),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to list boards: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_add_task(
    board_id: str,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    column_id: str = "todo",
) -> str:
    """
    添加任务到看板。

    Args:
        board_id: 看板ID
        title: 任务标题
        description: 可选的任务描述
        priority: 优先级 (low, medium, high)
        column_id: 目标列ID (todo, in_progress, done)

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 映射列ID到状态
        status_map = {
            "todo": "todo",
            "in_progress": "running",
            "done": "done",
        }
        status = status_map.get(column_id, "todo")

        # 优先级映射
        priority_map = {"low": 0, "medium": 1, "high": 2}
        priority_value = priority_map.get(priority, 1)

        task_id = _kanban_manager.create_task(
            board_id=board_id,
            title=title,
            body=description,
            status=status,
            priority=priority_value,
            created_by=_get_author(),
        )

        result = {
            "success": True,
            "task_id": task_id,
            "title": title,
            "message": f"任务已添加: {title}",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to add task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_move_task(
    board_id: str,
    task_id: str,
    target_column_id: str,
) -> str:
    """
    移动任务到另一列。

    Args:
        board_id: 看板ID
        task_id: 任务ID
        target_column_id: 目标列ID

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 映射列ID到状态
        status_map = {
            "todo": "todo",
            "in_progress": "running",
            "done": "done",
        }
        status = status_map.get(target_column_id, "todo")

        task = _kanban_manager.update_task(task_id, status=status)
        if task:
            result = {
                "success": True,
                "message": f"任务已移动到: {target_column_id}",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to move task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_update_task(
    board_id: str,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """
    更新任务。

    Args:
        board_id: 看板ID
        task_id: 任务ID
        title: 可选的新标题
        description: 可选的新描述
        priority: 可选的新优先级

    Returns:
        JSON 格式的结果字符串
    """
    try:
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["body"] = description
        if priority is not None:
            priority_map = {"low": 0, "medium": 1, "high": 2}
            updates["priority"] = priority_map.get(priority, 1)

        task = _kanban_manager.update_task(task_id, **updates)
        if task:
            result = {"success": True, "message": "任务已更新"}
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_delete_task(
    board_id: str,
    task_id: str,
) -> str:
    """
    删除任务。

    Args:
        board_id: 看板ID
        task_id: 任务ID

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.delete_task(task_id)
        if success:
            result = {"success": True, "message": "任务已删除"}
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_view_board(board_id: str) -> str:
    """
    查看看板详情。

    Args:
        board_id: 看板ID

    Returns:
        JSON 格式的结果字符串
    """
    try:
        board = _kanban_manager.get_board(board_id)
        if not board:
            result = {"success": False, "error": f"看板不存在: {board_id}"}
            return json.dumps(result, ensure_ascii=False)

        # 获取该看板的所有任务
        tasks = _kanban_manager.list_tasks(board_id=board_id, limit=500)

        # 按状态分组
        columns = {
            "todo": [],
            "in_progress": [],
            "done": [],
        }

        status_to_column = {
            "triage": "todo",
            "todo": "todo",
            "ready": "todo",
            "running": "in_progress",
            "blocked": "in_progress",
            "done": "done",
            "archived": "done",
            "timed_out": "done",
        }

        for task in tasks:
            task_dict = _task_to_dict(task)
            column_key = status_to_column.get(task.status, "todo")
            columns[column_key].append(task_dict)

        board_data = {
            "id": board.id,
            "name": board.name,
            "created_at": board.created_at,
            "tenant": board.tenant,
            "columns": [
                {"id": "todo", "name": "待办", "tasks": columns["todo"]},
                {"id": "in_progress", "name": "进行中", "tasks": columns["in_progress"]},
                {"id": "done", "name": "已完成", "tasks": columns["done"]},
            ],
        }

        result = {"success": True, "board": board_data}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to view board: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


# =============================================================================
# 新增工具函数
# =============================================================================

def kanban_create(
    board_id: Optional[str] = None,
    title: str = "",
    assignee: str = "",
    body: Optional[str] = None,
    parents: Optional[List[str]] = None,
    tenant: Optional[str] = None,
    priority: int = 0,
    workspace_kind: str = "scratch",
    workspace_path: Optional[str] = None,
    triage: bool = False,
    idempotency_key: Optional[str] = None,
    max_runtime_seconds: Optional[int] = None,
    initial_status: str = "running",
    skills: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    创建任务，支持完整参数。

    Args:
        board_id: 看板ID（可选，默认使用第一个看板）
        title: 任务标题
        assignee: 负责人
        body: 任务描述
        parents: 父任务ID列表
        tenant: 租户标识
        priority: 优先级（0-2）
        workspace_kind: 工作区类型
        workspace_path: 工作区路径
        triage: 是否在 triage 状态
        idempotency_key: 幂等键
        max_runtime_seconds: 最大运行时间
        initial_status: 初始状态
        skills: 技能列表
        session_id: 会话ID

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 使用默认看板如果没有指定
        if not board_id:
            board_id = _kanban_manager.get_default_board_id()
            if not board_id:
                result = {"success": False, "error": "没有可用的看板"}
                return json.dumps(result, ensure_ascii=False)

        # 设置初始状态
        if triage:
            initial_status = "triage"

        task_id = _kanban_manager.create_task(
            board_id=board_id,
            title=title,
            body=body,
            status=initial_status,  # 使用 initial_status 而不是硬编码 "todo"
            priority=priority,
            assignee=assignee if assignee else None,
            created_by=_get_author(),
            workspace_kind=workspace_kind,
            workspace_path=workspace_path,
            max_runtime_seconds=max_runtime_seconds,
            idempotency_key=idempotency_key,
            initial_status=initial_status,
            skills=skills,
            tenant=tenant,
            session_id=session_id,
        )

        # 添加父任务依赖
        if parents:
            for parent_id in parents:
                _kanban_manager.link_tasks(parent_id, task_id)

        result = {
            "success": True,
            "task_id": task_id,
            "title": title,
            "message": f"任务已创建: {title}",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_show(
    task_id: str,
    board: Optional[str] = None,
) -> str:
    """
    查看任务详情，返回完整信息（含评论/事件/运行历史/依赖）。

    Args:
        task_id: 任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        task = _kanban_manager.get_task(task_id)
        if not task:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
            return json.dumps(result, ensure_ascii=False)

        # 获取关联数据
        comments = _kanban_manager.get_comments(task_id)
        events = _kanban_manager.get_events(task_id)
        runs = _kanban_manager.get_runs(task_id)
        deps = _kanban_manager.get_dependencies(task_id)

        result = {
            "success": True,
            "task": _task_to_dict(task),
            "comments": [_comment_to_dict(c) for c in comments],
            "events": [_event_to_dict(e) for e in events],
            "runs": [_run_to_dict(r) for r in runs],
            "dependencies": deps,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to show task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_list(
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    tenant: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 50,
    board: Optional[str] = None,
) -> str:
    """
    列出任务，支持筛选器。

    Args:
        assignee: 负责人筛选
        status: 状态筛选
        tenant: 租户筛选
        include_archived: 包含已归档任务
        limit: 返回数量限制
        board: 看板ID筛选

    Returns:
        JSON 格式的结果字符串
    """
    try:
        tasks = _kanban_manager.list_tasks(
            board_id=board,
            assignee=assignee,
            status=status,
            tenant=tenant,
            include_archived=include_archived,
            limit=limit,
        )

        result = {
            "success": True,
            "tasks": [_task_to_dict(t) for t in tasks],
            "total": len(tasks),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_update(
    task_id: str,
    title: Optional[str] = None,
    body: Optional[str] = None,
    priority: Optional[int] = None,
    assignee: Optional[str] = None,
    board: Optional[str] = None,
) -> str:
    """
    更新任务（非状态）。

    Args:
        task_id: 任务ID
        title: 新标题
        body: 新描述
        priority: 新优先级
        assignee: 新负责人
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        updates = {}
        if title is not None:
            updates["title"] = title
        if body is not None:
            updates["body"] = body
        if priority is not None:
            updates["priority"] = priority
        if assignee is not None:
            updates["assignee"] = assignee

        task = _kanban_manager.update_task(task_id, **updates)
        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": "任务已更新",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_complete(
    task_id: Optional[str] = None,
    summary: Optional[str] = None,
    metadata: Optional[Dict] = None,
    result: Optional[str] = None,
    created_cards: Optional[List[str]] = None,
    artifacts: Optional[List[str]] = None,
    board: Optional[str] = None,
) -> str:
    """
    完成任务，支持 handoff 信息。

    Args:
        task_id: 任务ID
        summary: 完成摘要
        metadata: 元数据
        result: 结果
        created_cards: 创建的卡片ID列表
        artifacts: 产出物列表
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        if not task_id:
            result = {"success": False, "error": "task_id 是必填的"}
            return json.dumps(result, ensure_ascii=False)

        task = _kanban_manager.complete_task(
            task_id=task_id,
            result=result,
            summary=summary,
            metadata=metadata,
            created_cards=created_cards,
            artifacts=artifacts,
        )

        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": "任务已完成",
            }
        else:
            result = {"success": False, "error": f"任务不存在或无法完成: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        # 状态转换错误
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_block(
    task_id: str,
    reason: str,
    board: Optional[str] = None,
) -> str:
    """
    阻塞任务。

    Args:
        task_id: 任务ID
        reason: 阻塞原因
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        task = _kanban_manager.block_task(task_id, reason)
        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": f"任务已阻塞: {reason}",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to block task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_unblock(
    task_id: str,
    board: Optional[str] = None,
) -> str:
    """
    解阻塞任务（仅限 orchestrator）。

    Args:
        task_id: 任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        task = _kanban_manager.unblock_task(task_id)
        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": "任务已解除阻塞",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to unblock task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_heartbeat(
    task_id: Optional[str] = None,
    note: Optional[str] = None,
    board: Optional[str] = None,
) -> str:
    """
    心跳保活。

    Args:
        task_id: 任务ID（可选）
        note: 心跳备注
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 如果没有指定任务，获取当前运行中的任务
        if not task_id:
            tasks = _kanban_manager.list_tasks(status="running", limit=1)
            if tasks:
                task_id = tasks[0].id
            else:
                result = {"success": False, "error": "没有运行中的任务"}
                return json.dumps(result, ensure_ascii=False)

        task = _kanban_manager.get_task(task_id)
        if not task:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
            return json.dumps(result, ensure_ascii=False)

        # 添加心跳事件
        author = _get_author()
        if note:
            _kanban_manager.add_comment(task_id, author, f"[心跳] {note}")
        else:
            _kanban_manager.add_comment(task_id, author, "[心跳]")

        result = {
            "success": True,
            "task_id": task_id,
            "message": "心跳已记录",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to heartbeat: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_comment(
    task_id: str,
    body: str,
    board: Optional[str] = None,
) -> str:
    """
    添加评论。

    Args:
        task_id: 任务ID
        body: 评论内容
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        task = _kanban_manager.get_task(task_id)
        if not task:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
            return json.dumps(result, ensure_ascii=False)

        author = _get_author()
        comment = _kanban_manager.add_comment(task_id, author, body)

        result = {
            "success": True,
            "comment": _comment_to_dict(comment),
            "message": "评论已添加",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_link(
    parent_id: str,
    child_id: str,
    board: Optional[str] = None,
) -> str:
    """
    链接依赖关系（父任务完成后子任务变为 ready）。

    Args:
        parent_id: 父任务ID
        child_id: 子任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.link_tasks(parent_id, child_id)
        if success:
            result = {
                "success": True,
                "message": f"已链接: {parent_id} -> {child_id}",
            }
        else:
            result = {"success": False, "error": "依赖关系已存在"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to link tasks: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_unlink(
    parent_id: str,
    child_id: str,
    board: Optional[str] = None,
) -> str:
    """
    取消链接依赖关系。

    Args:
        parent_id: 父任务ID
        child_id: 子任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.unlink_tasks(parent_id, child_id)
        if success:
            result = {
                "success": True,
                "message": f"已取消链接: {parent_id} -> {child_id}",
            }
        else:
            result = {"success": False, "error": "依赖关系不存在"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to unlink tasks: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_delete(
    task_id: str,
    board: Optional[str] = None,
) -> str:
    """
    删除任务（新版实现）。

    Args:
        task_id: 任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.delete_task(task_id)
        if success:
            result = {"success": True, "message": "任务已删除"}
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def check_kanban_requirements() -> bool:
    """看板工具无外部依赖，始终可用"""
    return True


# =============================================================================
# 工具 Schema 定义
# =============================================================================

# 保留的工具 Schema
KANBAN_CREATE_BOARD_SCHEMA = {
    "name": "kanban_create_board",
    "description": "创建新的看板。",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "看板名称"},
        },
        "required": ["name"],
    },
}

KANBAN_DELETE_BOARD_SCHEMA = {
    "name": "kanban_delete_board",
    "description": "删除看板。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID"},
        },
        "required": ["board_id"],
    },
}

KANBAN_LIST_BOARDS_SCHEMA = {
    "name": "kanban_list_boards",
    "description": "列出所有看板。",
    "parameters": {"type": "object", "properties": {}},
}

KANBAN_ADD_TASK_SCHEMA = {
    "name": "kanban_add_task",
    "description": "添加任务到看板。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID"},
            "title": {"type": "string", "description": "任务标题"},
            "description": {"type": "string", "description": "任务描述"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "default": "medium",
                "description": "优先级",
            },
            "column_id": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "default": "todo",
                "description": "目标列",
            },
        },
        "required": ["board_id", "title"],
    },
}

KANBAN_MOVE_TASK_SCHEMA = {
    "name": "kanban_move_task",
    "description": "移动任务到不同列。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID"},
            "task_id": {"type": "string", "description": "任务ID"},
            "target_column_id": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "description": "目标列ID",
            },
        },
        "required": ["board_id", "task_id", "target_column_id"],
    },
}

KANBAN_UPDATE_TASK_SCHEMA = {
    "name": "kanban_update_task",
    "description": "更新任务详情。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID"},
            "task_id": {"type": "string", "description": "任务ID"},
            "title": {"type": "string", "description": "新标题"},
            "description": {"type": "string", "description": "新描述"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "新优先级",
            },
        },
        "required": ["board_id", "task_id"],
    },
}

KANBAN_DELETE_TASK_SCHEMA = {
    "name": "kanban_delete_task",
    "description": "从看板删除任务。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID"},
            "task_id": {"type": "string", "description": "任务ID"},
        },
        "required": ["board_id", "task_id"],
    },
}

KANBAN_VIEW_BOARD_SCHEMA = {
    "name": "kanban_view_board",
    "description": "查看看板完整详情。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID"},
        },
        "required": ["board_id"],
    },
}

# 新增工具 Schema
KANBAN_CREATE_SCHEMA = {
    "name": "kanban_create",
    "description": "创建任务，支持完整参数。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {"type": "string", "description": "看板ID（可选，默认使用第一个看板）"},
            "title": {"type": "string", "description": "任务标题"},
            "assignee": {"type": "string", "description": "负责人"},
            "body": {"type": "string", "description": "任务描述"},
            "parents": {"type": "array", "items": {"type": "string"}, "description": "父任务ID列表"},
            "tenant": {"type": "string", "description": "租户标识"},
            "priority": {"type": "integer", "default": 0, "description": "优先级（0-2）"},
            "workspace_kind": {"type": "string", "default": "scratch", "description": "工作区类型"},
            "workspace_path": {"type": "string", "description": "工作区路径"},
            "triage": {"type": "boolean", "default": False, "description": "是否在 triage 状态"},
            "idempotency_key": {"type": "string", "description": "幂等键"},
            "max_runtime_seconds": {"type": "integer", "description": "最大运行时间"},
            "initial_status": {"type": "string", "default": "running", "description": "初始状态"},
            "skills": {"type": "array", "items": {"type": "string"}, "description": "技能列表"},
            "session_id": {"type": "string", "description": "会话ID"},
        },
        "required": ["title"],
    },
}

KANBAN_SHOW_SCHEMA = {
    "name": "kanban_show",
    "description": "查看任务详情，返回完整信息（含评论/事件/运行历史/依赖）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}

KANBAN_LIST_SCHEMA = {
    "name": "kanban_list",
    "description": "列出任务，支持筛选器。",
    "parameters": {
        "type": "object",
        "properties": {
            "assignee": {"type": "string", "description": "负责人筛选"},
            "status": {"type": "string", "description": "状态筛选"},
            "tenant": {"type": "string", "description": "租户筛选"},
            "include_archived": {"type": "boolean", "default": False, "description": "包含已归档任务"},
            "limit": {"type": "integer", "default": 50, "description": "返回数量限制"},
            "board": {"type": "string", "description": "看板ID筛选"},
        },
    },
}

KANBAN_UPDATE_SCHEMA = {
    "name": "kanban_update",
    "description": "更新任务（非状态）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "title": {"type": "string", "description": "新标题"},
            "body": {"type": "string", "description": "新描述"},
            "priority": {"type": "integer", "description": "新优先级"},
            "assignee": {"type": "string", "description": "新负责人"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}

KANBAN_COMPLETE_SCHEMA = {
    "name": "kanban_complete",
    "description": "完成任务，支持 handoff 信息。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "summary": {"type": "string", "description": "完成摘要"},
            "metadata": {"type": "object", "description": "元数据"},
            "result": {"type": "string", "description": "结果"},
            "created_cards": {"type": "array", "items": {"type": "string"}, "description": "创建的卡片ID列表"},
            "artifacts": {"type": "array", "items": {"type": "string"}, "description": "产出物列表"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
    },
}

KANBAN_BLOCK_SCHEMA = {
    "name": "kanban_block",
    "description": "阻塞任务。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "reason": {"type": "string", "description": "阻塞原因"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id", "reason"],
    },
}

KANBAN_UNBLOCK_SCHEMA = {
    "name": "kanban_unblock",
    "description": "解阻塞任务（仅限 orchestrator）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}

KANBAN_HEARTBEAT_SCHEMA = {
    "name": "kanban_heartbeat",
    "description": "心跳保活。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID（可选，默认使用运行中的任务）"},
            "note": {"type": "string", "description": "心跳备注"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
    },
}

KANBAN_COMMENT_SCHEMA = {
    "name": "kanban_comment",
    "description": "添加评论。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "body": {"type": "string", "description": "评论内容"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id", "body"],
    },
}

KANBAN_LINK_SCHEMA = {
    "name": "kanban_link",
    "description": "链接依赖关系（父任务完成后子任务变为 ready）。",
    "parameters": {
        "type": "object",
        "properties": {
            "parent_id": {"type": "string", "description": "父任务ID"},
            "child_id": {"type": "string", "description": "子任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["parent_id", "child_id"],
    },
}

KANBAN_UNLINK_SCHEMA = {
    "name": "kanban_unlink",
    "description": "取消链接依赖关系。",
    "parameters": {
        "type": "object",
        "properties": {
            "parent_id": {"type": "string", "description": "父任务ID"},
            "child_id": {"type": "string", "description": "子任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["parent_id", "child_id"],
    },
}

KANBAN_DELETE_SCHEMA = {
    "name": "kanban_delete",
    "description": "删除任务（新版实现）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}


# =============================================================================
# 工具注册
# =============================================================================

# 保留的工具注册
registry.register(
    name="kanban_create_board",
    toolset="kanban",
    schema=KANBAN_CREATE_BOARD_SCHEMA,
    handler=lambda args, **kw: kanban_create_board(args.get("name", "")),
    check_fn=check_kanban_requirements,
    emoji="📋",
)

registry.register(
    name="kanban_delete_board",
    toolset="kanban",
    schema=KANBAN_DELETE_BOARD_SCHEMA,
    handler=lambda args, **kw: kanban_delete_board(args.get("board_id", "")),
    check_fn=check_kanban_requirements,
    emoji="🗑️",
)

registry.register(
    name="kanban_list_boards",
    toolset="kanban",
    schema=KANBAN_LIST_BOARDS_SCHEMA,
    handler=lambda args, **kw: kanban_list_boards(),
    check_fn=check_kanban_requirements,
    emoji="📋",
)

registry.register(
    name="kanban_add_task",
    toolset="kanban",
    schema=KANBAN_ADD_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_add_task(
        board_id=args.get("board_id", ""),
        title=args.get("title", ""),
        description=args.get("description"),
        priority=args.get("priority", "medium"),
        column_id=args.get("column_id", "todo"),
    ),
    check_fn=check_kanban_requirements,
    emoji="➕",
)

registry.register(
    name="kanban_move_task",
    toolset="kanban",
    schema=KANBAN_MOVE_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_move_task(
        board_id=args.get("board_id", ""),
        task_id=args.get("task_id", ""),
        target_column_id=args.get("target_column_id", ""),
    ),
    check_fn=check_kanban_requirements,
    emoji="➡️",
)

registry.register(
    name="kanban_update_task",
    toolset="kanban",
    schema=KANBAN_UPDATE_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_update_task(
        board_id=args.get("board_id", ""),
        task_id=args.get("task_id", ""),
        title=args.get("title"),
        description=args.get("description"),
        priority=args.get("priority"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✏️",
)

registry.register(
    name="kanban_delete_task",
    toolset="kanban",
    schema=KANBAN_DELETE_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_delete_task(
        board_id=args.get("board_id", ""),
        task_id=args.get("task_id", ""),
    ),
    check_fn=check_kanban_requirements,
    emoji="🗑️",
)

registry.register(
    name="kanban_view_board",
    toolset="kanban",
    schema=KANBAN_VIEW_BOARD_SCHEMA,
    handler=lambda args, **kw: kanban_view_board(args.get("board_id", "")),
    check_fn=check_kanban_requirements,
    emoji="👁️",
)

# 新增工具注册
registry.register(
    name="kanban_create",
    toolset="kanban",
    schema=KANBAN_CREATE_SCHEMA,
    handler=lambda args, **kw: kanban_create(
        board_id=args.get("board_id"),
        title=args.get("title", ""),
        assignee=args.get("assignee", ""),
        body=args.get("body"),
        parents=args.get("parents"),
        tenant=args.get("tenant"),
        priority=args.get("priority", 0),
        workspace_kind=args.get("workspace_kind", "scratch"),
        workspace_path=args.get("workspace_path"),
        triage=args.get("triage", False),
        idempotency_key=args.get("idempotency_key"),
        max_runtime_seconds=args.get("max_runtime_seconds"),
        initial_status=args.get("initial_status", "running"),
        skills=args.get("skills"),
        session_id=args.get("session_id"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✨",
)

registry.register(
    name="kanban_show",
    toolset="kanban",
    schema=KANBAN_SHOW_SCHEMA,
    handler=lambda args, **kw: kanban_show(
        task_id=args.get("task_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🔍",
)

registry.register(
    name="kanban_list",
    toolset="kanban",
    schema=KANBAN_LIST_SCHEMA,
    handler=lambda args, **kw: kanban_list(
        assignee=args.get("assignee"),
        status=args.get("status"),
        tenant=args.get("tenant"),
        include_archived=args.get("include_archived", False),
        limit=args.get("limit", 50),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="📝",
)

registry.register(
    name="kanban_update",
    toolset="kanban",
    schema=KANBAN_UPDATE_SCHEMA,
    handler=lambda args, **kw: kanban_update(
        task_id=args.get("task_id", ""),
        title=args.get("title"),
        body=args.get("body"),
        priority=args.get("priority"),
        assignee=args.get("assignee"),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✏️",
)

registry.register(
    name="kanban_complete",
    toolset="kanban",
    schema=KANBAN_COMPLETE_SCHEMA,
    handler=lambda args, **kw: kanban_complete(
        task_id=args.get("task_id"),
        summary=args.get("summary"),
        metadata=args.get("metadata"),
        result=args.get("result"),
        created_cards=args.get("created_cards"),
        artifacts=args.get("artifacts"),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✅",
)

registry.register(
    name="kanban_block",
    toolset="kanban",
    schema=KANBAN_BLOCK_SCHEMA,
    handler=lambda args, **kw: kanban_block(
        task_id=args.get("task_id", ""),
        reason=args.get("reason", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🚫",
)

registry.register(
    name="kanban_unblock",
    toolset="kanban",
    schema=KANBAN_UNBLOCK_SCHEMA,
    handler=lambda args, **kw: kanban_unblock(
        task_id=args.get("task_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🔓",
)

registry.register(
    name="kanban_heartbeat",
    toolset="kanban",
    schema=KANBAN_HEARTBEAT_SCHEMA,
    handler=lambda args, **kw: kanban_heartbeat(
        task_id=args.get("task_id"),
        note=args.get("note"),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="💓",
)

registry.register(
    name="kanban_comment",
    toolset="kanban",
    schema=KANBAN_COMMENT_SCHEMA,
    handler=lambda args, **kw: kanban_comment(
        task_id=args.get("task_id", ""),
        body=args.get("body", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="💬",
)

registry.register(
    name="kanban_link",
    toolset="kanban",
    schema=KANBAN_LINK_SCHEMA,
    handler=lambda args, **kw: kanban_link(
        parent_id=args.get("parent_id", ""),
        child_id=args.get("child_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🔗",
)

registry.register(
    name="kanban_unlink",
    toolset="kanban",
    schema=KANBAN_UNLINK_SCHEMA,
    handler=lambda args, **kw: kanban_unlink(
        parent_id=args.get("parent_id", ""),
        child_id=args.get("child_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✂️",
)

registry.register(
    name="kanban_delete",
    toolset="kanban",
    schema=KANBAN_DELETE_SCHEMA,
    handler=lambda args, **kw: kanban_delete(
        task_id=args.get("task_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🗑️",
)