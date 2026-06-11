#!/usr/bin/env python3
"""
Kanban Tool 测试用例

测试 Kanban 功能的数据库层和工具函数层。
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_db_path(tmp_path):
    """测试数据库路径"""
    return str(tmp_path / "test_kanban.db")


@pytest.fixture
def kanban_db(test_db_path):
    """KanbanDB 实例"""
    from tools.kanban_db import KanbanDB

    db = KanbanDB(test_db_path)
    db.init_schema()
    yield db
    db.close()


# =============================================================================
# TestKanbanDB - 数据库层测试
# =============================================================================


class TestKanbanDB:
    """测试 KanbanDB 数据库层"""

    def test_init_schema(self, kanban_db):
        """测试数据库 Schema 初始化"""
        conn = kanban_db.connect()
        # 验证表存在
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor]
        assert "boards" in tables
        assert "tasks" in tables
        assert "task_dependencies" in tables
        assert "comments" in tables
        assert "events" in tables
        assert "task_runs" in tables
        assert "task_claims" in tables
        conn.close()

    def test_connection(self, kanban_db):
        """测试数据库连接"""
        conn = kanban_db.connect()
        assert conn is not None
        assert conn.row_factory is not None
        kanban_db.close()

    def test_multiple_connections(self, kanban_db):
        """测试多次连接获取同一连接"""
        conn1 = kanban_db.connect()
        conn2 = kanban_db.connect()
        assert conn1 is conn2
        kanban_db.close()


# =============================================================================
# TestBoards - 看板 CRUD 测试
# =============================================================================


class TestBoards:
    """测试 Board 操作"""

    def test_board_create(self, kanban_db):
        """测试创建看板"""
        from tools.kanban_db import board_create

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board", tenant="test")
        assert board is not None
        assert board.name == "Test Board"
        assert board.tenant == "test"
        assert board.id is not None
        conn.close()

    def test_board_create_without_tenant(self, kanban_db):
        """测试创建看板（无租户）"""
        from tools.kanban_db import board_create

        conn = kanban_db.connect()
        board = board_create(conn, name="No Tenant Board")
        assert board is not None
        assert board.tenant is None
        conn.close()

    def test_board_get(self, kanban_db):
        """测试获取看板"""
        from tools.kanban_db import board_create, board_get

        conn = kanban_db.connect()
        created = board_create(conn, name="Get Test")
        board = board_get(conn, created.id)
        assert board is not None
        assert board.id == created.id
        assert board.name == "Get Test"
        conn.close()

    def test_board_get_not_found(self, kanban_db):
        """测试获取不存在的看板"""
        from tools.kanban_db import board_get

        conn = kanban_db.connect()
        board = board_get(conn, "non-existent-id")
        assert board is None
        conn.close()

    def test_board_list(self, kanban_db):
        """测试列出看板"""
        from tools.kanban_db import board_create, board_list

        conn = kanban_db.connect()
        board_create(conn, name="Board 1")
        board_create(conn, name="Board 2")
        boards = board_list(conn)
        assert len(boards) >= 2
        conn.close()

    def test_board_update(self, kanban_db):
        """测试更新看板"""
        from tools.kanban_db import board_create

        conn = kanban_db.connect()
        board = board_create(conn, name="Original Name")
        cursor = conn.cursor()
        cursor.execute("UPDATE boards SET name = ? WHERE id = ?", ("Updated Name", board.id))
        conn.commit()
        cursor.execute("SELECT * FROM boards WHERE id = ?", (board.id,))
        row = cursor.fetchone()
        assert row["name"] == "Updated Name"
        conn.close()

    def test_board_delete(self, kanban_db):
        """测试删除看板"""
        from tools.kanban_db import board_create, board_delete, board_get

        conn = kanban_db.connect()
        board = board_create(conn, name="To Delete")
        result = board_delete(conn, board.id)
        assert result is True
        board = board_get(conn, board.id)
        assert board is None
        conn.close()

    def test_board_delete_with_tasks(self, kanban_db):
        """测试删除看板（同时删除任务）"""
        from tools.kanban_db import board_create, board_delete, board_get, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Board With Tasks")
        task_id = task_create(conn, board.id, title="Task 1")
        task_id2 = task_create(conn, board.id, title="Task 2")

        # 验证任务存在
        assert task_get(conn, task_id) is not None
        assert task_get(conn, task_id2) is not None

        # 删除看板
        result = board_delete(conn, board.id)
        assert result is True

        # 验证任务已被删除
        assert task_get(conn, task_id) is None
        assert task_get(conn, task_id2) is None
        conn.close()


# =============================================================================
# TestTasks - 任务 CRUD 测试
# =============================================================================


class TestTasks:
    """测试 Task 操作"""

    def test_task_create(self, kanban_db):
        """测试创建任务"""
        from tools.kanban_db import board_create, task_create

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(
            conn, board.id, title="Test Task", status="todo", priority=1
        )
        assert task_id is not None
        from tools.kanban_db import task_get

        task = task_get(conn, task_id)
        assert task.title == "Test Task"
        assert task.status == "todo"
        assert task.priority == 1
        conn.close()

    def test_task_create_with_body(self, kanban_db):
        """测试创建带描述的任务"""
        from tools.kanban_db import board_create, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(
            conn, board.id, title="Task", body="This is a description"
        )
        task = task_get(conn, task_id)
        assert task.body == "This is a description"
        conn.close()

    def test_task_create_with_assignee(self, kanban_db):
        """测试创建带负责人的任务"""
        from tools.kanban_db import board_create, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(
            conn, board.id, title="Task", assignee="worker-1", created_by="creator-1"
        )
        task = task_get(conn, task_id)
        assert task.assignee == "worker-1"
        assert task.created_by == "creator-1"
        conn.close()

    def test_task_get(self, kanban_db):
        """测试获取任务"""
        from tools.kanban_db import board_create, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Get Test")
        task = task_get(conn, task_id)
        assert task is not None
        assert task.id == task_id
        assert task.title == "Get Test"
        conn.close()

    def test_task_get_not_found(self, kanban_db):
        """测试获取不存在的任务"""
        from tools.kanban_db import task_get

        conn = kanban_db.connect()
        task = task_get(conn, "non-existent-id")
        assert task is None
        conn.close()

    def test_task_list(self, kanban_db):
        """测试列出任务"""
        from tools.kanban_db import board_create, task_create, task_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_create(conn, board.id, title="Task 1")
        task_create(conn, board.id, title="Task 2")
        tasks = task_list(conn)
        assert len(tasks) >= 2
        conn.close()

    def test_task_list_with_filter(self, kanban_db):
        """测试带筛选条件列出任务"""
        from tools.kanban_db import board_create, task_create, task_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_create(conn, board.id, title="Task 1", status="todo")
        task_create(conn, board.id, title="Task 2", status="running")
        task_create(conn, board.id, title="Task 3", status="todo")

        # 按状态筛选
        todo_tasks = task_list(conn, status="todo")
        assert len(todo_tasks) == 2

        running_tasks = task_list(conn, status="running")
        assert len(running_tasks) == 1
        conn.close()

    def test_task_list_by_board(self, kanban_db):
        """测试按看板筛选任务"""
        from tools.kanban_db import board_create, task_create, task_list

        conn = kanban_db.connect()
        board1 = board_create(conn, name="Board 1")
        board2 = board_create(conn, name="Board 2")
        task_create(conn, board1.id, title="Task 1")
        task_create(conn, board1.id, title="Task 2")
        task_create(conn, board2.id, title="Task 3")

        tasks_board1 = task_list(conn, board_id=board1.id)
        assert len(tasks_board1) == 2

        tasks_board2 = task_list(conn, board_id=board2.id)
        assert len(tasks_board2) == 1
        conn.close()

    def test_task_update(self, kanban_db):
        """测试更新任务"""
        from tools.kanban_db import board_create, task_create, task_update, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Original")
        task_update(conn, task_id, title="Updated", priority=2)
        task = task_get(conn, task_id)
        assert task.title == "Updated"
        assert task.priority == 2
        conn.close()

    def test_task_update_multiple_fields(self, kanban_db):
        """测试更新多个字段"""
        from tools.kanban_db import board_create, task_create, task_update, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Original", body="Old body")
        task_update(
            conn,
            task_id,
            title="New Title",
            body="New body",
            assignee="new-assignee",
            priority=1,
        )
        task = task_get(conn, task_id)
        assert task.title == "New Title"
        assert task.body == "New body"
        assert task.assignee == "new-assignee"
        assert task.priority == 1
        conn.close()

    def test_task_delete(self, kanban_db):
        """测试删除任务"""
        from tools.kanban_db import board_create, task_create, task_delete, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="To Delete")
        result = task_delete(conn, task_id)
        assert result is True
        task = task_get(conn, task_id)
        assert task is None
        conn.close()

    def test_task_delete_with_related_data(self, kanban_db):
        """测试删除任务（同时删除关联数据）"""
        from tools.kanban_db import (
            board_create,
            task_create,
            task_delete,
            task_get,
            comment_add,
            comment_list,
            event_add,
            event_list,
        )

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Task with data")
        comment_add(conn, task_id, "user1", "Test comment")
        event_add(conn, task_id, "created")

        # 验证关联数据存在
        assert len(comment_list(conn, task_id)) == 1
        assert len(event_list(conn, task_id)) == 1

        # 删除任务
        task_delete(conn, task_id)

        # 验证关联数据已删除
        assert len(comment_list(conn, task_id)) == 0
        assert len(event_list(conn, task_id)) == 0
        conn.close()


# =============================================================================
# TestTaskState - 任务状态转换测试
# =============================================================================


class TestTaskState:
    """测试任务状态转换"""

    def test_task_start_from_ready(self, kanban_db):
        """测试从 ready 状态开始任务"""
        from tools.kanban_db import board_create, task_create, task_start, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="ready")
        task = task_start(conn, task_id)
        assert task is not None
        assert task.status == "running"
        assert task.started_at is not None
        conn.close()

    def test_task_start_invalid_status(self, kanban_db):
        """测试非法状态转换"""
        from tools.kanban_db import board_create, task_create, task_start

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="todo")

        with pytest.raises(ValueError, match="Cannot start task"):
            task_start(conn, task_id)
        conn.close()

    def test_task_complete(self, kanban_db):
        """测试任务完成"""
        from tools.kanban_db import board_create, task_create, task_complete, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="running")
        task = task_complete(conn, task_id, summary="Done")
        assert task is not None
        assert task.status == "done"
        assert task.completed_at is not None
        conn.close()

    def test_task_complete_with_result(self, kanban_db):
        """测试任务完成（带结果）"""
        from tools.kanban_db import board_create, task_create, task_complete, event_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="running")
        task_complete(
            conn,
            task_id,
            result="Task result",
            summary="Summary",
            metadata={"key": "value"},
        )

        events = event_list(conn, task_id)
        assert len(events) >= 1
        # 查找完成事件
        completed_events = [e for e in events if e.kind == "completed"]
        assert len(completed_events) == 1
        conn.close()

    def test_task_complete_invalid_status(self, kanban_db):
        """测试非法状态完成"""
        from tools.kanban_db import board_create, task_create, task_complete

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="todo")

        with pytest.raises(ValueError, match="Cannot complete task"):
            task_complete(conn, task_id)
        conn.close()

    def test_task_block(self, kanban_db):
        """测试任务阻塞"""
        from tools.kanban_db import board_create, task_create, task_block, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="running")
        task = task_block(conn, task_id, reason="Need input")
        assert task is not None
        assert task.status == "blocked"
        assert task.blocked_reason == "Need input"
        conn.close()

    def test_task_block_invalid_status(self, kanban_db):
        """测试非法状态阻塞"""
        from tools.kanban_db import board_create, task_create, task_block

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="todo")

        with pytest.raises(ValueError, match="Cannot block task"):
            task_block(conn, task_id, reason="test")
        conn.close()

    def test_task_unblock(self, kanban_db):
        """测试任务解阻塞"""
        from tools.kanban_db import board_create, task_create, task_block, task_unblock, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="running")
        task_block(conn, task_id, reason="Need input")
        task = task_unblock(conn, task_id)
        assert task is not None
        assert task.status == "ready"
        assert task.blocked_reason is None
        conn.close()

    def test_task_unblock_invalid_status(self, kanban_db):
        """测试非阻塞状态解阻塞"""
        from tools.kanban_db import board_create, task_create, task_unblock

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="running")

        with pytest.raises(ValueError, match="Cannot unblock task"):
            task_unblock(conn, task_id)
        conn.close()

    def test_task_archive(self, kanban_db):
        """测试任务归档"""
        from tools.kanban_db import board_create, task_create, task_archive, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="done")
        task = task_archive(conn, task_id)
        assert task is not None
        assert task.status == "archived"
        conn.close()


# =============================================================================
# TestDependencies - 依赖管理测试
# =============================================================================


class TestDependencies:
    """测试任务依赖"""

    def test_dep_link(self, kanban_db):
        """测试链接依赖"""
        from tools.kanban_db import board_create, task_create, dep_link, dep_parent_ids

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent_id = task_create(conn, board.id, title="Parent")
        child_id = task_create(conn, board.id, title="Child")

        result = dep_link(conn, parent_id, child_id)
        assert result is True

        parents = dep_parent_ids(conn, child_id)
        assert parent_id in parents
        conn.close()

    def test_dep_link_duplicate(self, kanban_db):
        """测试重复链接"""
        from tools.kanban_db import board_create, task_create, dep_link

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent_id = task_create(conn, board.id, title="Parent")
        child_id = task_create(conn, board.id, title="Child")

        dep_link(conn, parent_id, child_id)
        result = dep_link(conn, parent_id, child_id)
        assert result is False
        conn.close()

    def test_dep_unlink(self, kanban_db):
        """测试取消链接"""
        from tools.kanban_db import board_create, task_create, dep_link, dep_unlink, dep_parent_ids

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent_id = task_create(conn, board.id, title="Parent")
        child_id = task_create(conn, board.id, title="Child")

        dep_link(conn, parent_id, child_id)
        result = dep_unlink(conn, parent_id, child_id)
        assert result is True

        parents = dep_parent_ids(conn, child_id)
        assert parent_id not in parents
        conn.close()

    def test_dep_child_ids(self, kanban_db):
        """测试获取子任务ID列表"""
        from tools.kanban_db import board_create, task_create, dep_link, dep_child_ids

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent_id = task_create(conn, board.id, title="Parent")
        child1_id = task_create(conn, board.id, title="Child 1")
        child2_id = task_create(conn, board.id, title="Child 2")

        dep_link(conn, parent_id, child1_id)
        dep_link(conn, parent_id, child2_id)

        children = dep_child_ids(conn, parent_id)
        assert child1_id in children
        assert child2_id in children
        conn.close()

    def test_dep_cycle_detection_direct(self, kanban_db):
        """测试直接循环依赖检测"""
        from tools.kanban_db import board_create, task_create, dep_link

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task1 = task_create(conn, board.id, title="Task 1")
        task2 = task_create(conn, board.id, title="Task 2")

        # 尝试创建循环：task1 -> task2 -> task1
        dep_link(conn, task1, task2)
        with pytest.raises(ValueError, match="循环依赖|cycle"):
            dep_link(conn, task2, task1)
        conn.close()

    def test_dep_cycle_detection_self_loop(self, kanban_db):
        """测试自循环检测"""
        from tools.kanban_db import board_create, task_create, dep_link

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task = task_create(conn, board.id, title="Task")

        with pytest.raises(ValueError, match="循环依赖|cycle"):
            dep_link(conn, task, task)
        conn.close()

    def test_dep_promote_on_complete(self, kanban_db):
        """测试父任务完成时自动提升子任务"""
        from tools.kanban_db import (
            board_create,
            task_create,
            task_complete,
            dep_link,
            task_get,
        )

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent_id = task_create(conn, board.id, title="Parent", status="ready")
        child_id = task_create(conn, board.id, title="Child", status="todo")

        dep_link(conn, parent_id, child_id)

        # 子任务应该还是 todo
        child = task_get(conn, child_id)
        assert child.status == "todo"

        # 父任务变为 running
        from tools.kanban_db import task_start

        task_start(conn, parent_id)

        # 父任务完成
        task_complete(conn, parent_id)

        # 子任务应该变为 ready
        child = task_get(conn, child_id)
        assert child.status == "ready"
        conn.close()

    def test_dep_not_promote_until_all_done(self, kanban_db):
        """测试所有父任务完成才提升"""
        from tools.kanban_db import (
            board_create,
            task_create,
            task_start,
            task_complete,
            dep_link,
            task_get,
        )

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent1_id = task_create(conn, board.id, title="Parent 1", status="ready")
        parent2_id = task_create(conn, board.id, title="Parent 2", status="todo")
        child_id = task_create(conn, board.id, title="Child", status="todo")

        dep_link(conn, parent1_id, child_id)
        dep_link(conn, parent2_id, child_id)

        # 父任务1完成
        task_start(conn, parent1_id)
        task_complete(conn, parent1_id)

        # 子任务应该还是 todo（因为 parent2 未完成）
        child = task_get(conn, child_id)
        assert child.status == "todo"
        conn.close()


# =============================================================================
# TestComments - 评论系统测试
# =============================================================================


class TestComments:
    """测试评论功能"""

    def test_comment_add(self, kanban_db):
        """测试添加评论"""
        from tools.kanban_db import board_create, task_create, comment_add, comment_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        comment = comment_add(conn, task_id, author="user1", body="Test comment")
        assert comment is not None
        assert comment.author == "user1"
        assert comment.body == "Test comment"

        comments = comment_list(conn, task_id)
        assert len(comments) == 1
        assert comments[0].body == "Test comment"
        conn.close()

    def test_comment_add_multiple(self, kanban_db):
        """测试添加多条评论"""
        from tools.kanban_db import board_create, task_create, comment_add, comment_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        comment_add(conn, task_id, author="user1", body="Comment 1")
        comment_add(conn, task_id, author="user2", body="Comment 2")
        comment_add(conn, task_id, author="user1", body="Comment 3")

        comments = comment_list(conn, task_id)
        assert len(comments) == 3
        conn.close()

    def test_comment_list_ordered(self, kanban_db):
        """测试评论按时间排序"""
        from tools.kanban_db import board_create, task_create, comment_add, comment_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        comment_add(conn, task_id, author="user1", body="First")
        comment_add(conn, task_id, author="user2", body="Second")
        comment_add(conn, task_id, author="user3", body="Third")

        comments = comment_list(conn, task_id)
        assert comments[0].body == "First"
        assert comments[1].body == "Second"
        assert comments[2].body == "Third"
        conn.close()


# =============================================================================
# TestEvents - 事件系统测试
# =============================================================================


class TestEvents:
    """测试事件功能"""

    def test_event_add(self, kanban_db):
        """测试添加事件"""
        from tools.kanban_db import board_create, task_create, event_add, event_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        event = event_add(
            conn, task_id, kind="status_change", payload='{"from": "todo", "to": "running"}'
        )
        assert event is not None
        assert event.kind == "status_change"
        assert event.task_id == task_id

        events = event_list(conn, task_id)
        assert len(events) >= 1
        conn.close()

    def test_event_list_ordered(self, kanban_db):
        """测试事件按时间倒序"""
        from tools.kanban_db import board_create, task_create, event_add, event_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        event_add(conn, task_id, kind="event1")
        event_add(conn, task_id, kind="event2")
        event_add(conn, task_id, kind="event3")

        events = event_list(conn, task_id)
        # 最新事件在前
        assert events[0].kind == "event3"
        assert events[2].kind == "event1"
        conn.close()

    def test_event_list_with_limit(self, kanban_db):
        """测试限制事件数量"""
        from tools.kanban_db import board_create, task_create, event_add, event_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        for i in range(10):
            event_add(conn, task_id, kind=f"event{i}")

        events = event_list(conn, task_id, limit=5)
        assert len(events) == 5
        conn.close()


# =============================================================================
# TestRuns - 运行记录测试
# =============================================================================


class TestRuns:
    """测试运行记录功能"""

    def test_run_start(self, kanban_db):
        """测试开始运行记录"""
        from tools.kanban_db import board_create, task_create, run_start

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        run = run_start(conn, task_id, profile="worker-1")
        assert run is not None
        assert run.task_id == task_id
        assert run.status == "running"
        assert run.started_at is not None
        conn.close()

    def test_run_end(self, kanban_db):
        """测试结束运行记录"""
        from tools.kanban_db import board_create, task_create, run_start, run_end, run_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        run = run_start(conn, task_id)
        run = run_end(
            conn,
            run.id,
            status="completed",
            outcome="success",
            summary="Task completed successfully",
        )

        assert run is not None
        assert run.status == "completed"
        assert run.outcome == "success"
        assert run.ended_at is not None
        conn.close()

    def test_run_list(self, kanban_db):
        """测试列出运行记录"""
        from tools.kanban_db import board_create, task_create, run_start, run_end, run_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test")

        run1 = run_start(conn, task_id)
        run_end(conn, run1.id, status="failed", error="Error 1")

        run2 = run_start(conn, task_id)
        run_end(conn, run2.id, status="completed", outcome="success")

        runs = run_list(conn, task_id)
        assert len(runs) == 2
        conn.close()


# =============================================================================
# TestIdempotency - 幂等键测试
# =============================================================================


class TestIdempotency:
    """测试幂等键防重"""

    def test_idempotency_key(self, kanban_db):
        """测试幂等键"""
        from tools.kanban_db import board_create, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")

        task_id1 = task_create(
            conn, board.id, title="Task", idempotency_key="unique-key-123"
        )
        task_id2 = task_create(
            conn, board.id, title="Task", idempotency_key="unique-key-123"
        )

        # 应该返回相同的 task_id
        assert task_id1 == task_id2

        # 验证只创建了一个任务
        task = task_get(conn, task_id1)
        assert task is not None
        conn.close()

    def test_idempotency_key_different_keys(self, kanban_db):
        """测试不同幂等键创建不同任务"""
        from tools.kanban_db import board_create, task_create

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")

        task_id1 = task_create(
            conn, board.id, title="Task", idempotency_key="key-1"
        )
        task_id2 = task_create(
            conn, board.id, title="Task", idempotency_key="key-2"
        )

        # 应该返回不同的 task_id
        assert task_id1 != task_id2
        conn.close()

    def test_task_find_by_idempotency_key(self, kanban_db):
        """测试通过幂等键查找任务"""
        from tools.kanban_db import board_create, task_create, task_find_by_idempotency_key

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")

        task_create(conn, board.id, title="Task", idempotency_key="find-key")
        task = task_find_by_idempotency_key(conn, "find-key")

        assert task is not None
        assert task.title == "Task"
        conn.close()


# =============================================================================
# TestClaims - 认领系统测试
# =============================================================================


class TestClaims:
    """测试任务认领"""

    def test_claim_task(self, kanban_db):
        """测试认领任务"""
        from tools.kanban_db import board_create, task_create, claim_task, claim_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="ready")

        claim = claim_task(conn, task_id, "worker-1")
        assert claim is not None
        assert claim.claimer == "worker-1"
        assert claim.task_id == task_id

        result = claim_get(conn, task_id)
        assert result is not None
        assert result.claimer == "worker-1"
        conn.close()

    def test_claim_release(self, kanban_db):
        """测试释放认领"""
        from tools.kanban_db import board_create, task_create, claim_task, claim_release, claim_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="ready")

        claim_task(conn, task_id, "worker-1")
        result = claim_release(conn, task_id)
        assert result is True

        claim = claim_get(conn, task_id)
        assert claim is None
        conn.close()

    def test_claim_heartbeat(self, kanban_db):
        """测试认领心跳"""
        from tools.kanban_db import board_create, task_create, claim_task, claim_heartbeat, claim_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="ready")

        claim_task(conn, task_id, "worker-1")
        original_claim = claim_get(conn, task_id)
        original_time = original_claim.heartbeat_at

        result = claim_heartbeat(conn, task_id, "worker-1")
        assert result is True

        updated_claim = claim_get(conn, task_id)
        assert updated_claim.heartbeat_at != original_time
        conn.close()

    def test_claim_release_stale(self, kanban_db):
        """测试回收陈旧认领"""
        from tools.kanban_db import board_create, task_create, claim_task, claim_release_stale, claim_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_id = task_create(conn, board.id, title="Test", status="ready")

        claim_task(conn, task_id, "worker-1")

        # 模拟陈旧认领（直接修改 claimed_at）
        conn.execute(
            "UPDATE task_claims SET claimed_at = datetime('now', '-1 hour'), heartbeat_at = datetime('now', '-1 hour') WHERE task_id = ?",
            (task_id,),
        )
        conn.commit()

        # 回收 30 秒以上的陈旧认领
        released = claim_release_stale(conn, max_age_seconds=30)
        assert released >= 1

        claim = claim_get(conn, task_id)
        assert claim is None
        conn.close()


# =============================================================================
# TestRecomputeReady - 重新计算就绪状态测试
# =============================================================================


class TestRecomputeReady:
    """测试重新计算任务就绪状态"""

    def test_recompute_ready(self, kanban_db):
        """测试 recompute_ready 函数"""
        from tools.kanban_db import (
            board_create,
            task_create,
            task_update,
            recompute_ready,
            task_get,
        )

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        parent_id = task_create(conn, board.id, title="Parent", status="todo")
        child_id = task_create(conn, board.id, title="Child", status="todo")

        from tools.kanban_db import dep_link

        dep_link(conn, parent_id, child_id)

        # 父任务未完成，子任务不应就绪
        child = task_get(conn, child_id)
        assert child.status == "todo"

        # 父任务完成
        task_update(conn, parent_id, status="done")

        # 调用 recompute_ready
        promoted = recompute_ready(conn)
        assert promoted >= 1

        # 子任务应该变为 ready
        child = task_get(conn, child_id)
        assert child.status == "ready"
        conn.close()

    def test_recompute_ready_no_parents(self, kanban_db):
        """测试无父任务的任务不变化"""
        from tools.kanban_db import board_create, task_create, recompute_ready

        conn = kanban_db.connect()
        board = board_create(conn, name="Test Board")
        task_create(conn, board.id, title="Independent Task", status="todo")

        promoted = recompute_ready(conn)
        assert promoted == 0
        conn.close()


# =============================================================================
# TestToolFunctions - 工具函数测试
# =============================================================================


class TestToolFunctions:
    """测试 kanban_tool 工具函数"""

    def test_kanban_create_board(self):
        """测试 kanban_create_board 函数"""
        from tools.kanban_tool import kanban_create_board

        result = kanban_create_board("Test Board")
        data = json.loads(result)
        assert data.get("success") is True
        assert "board_id" in data

    def test_kanban_list_boards(self):
        """测试 kanban_list_boards 函数"""
        from tools.kanban_tool import kanban_list_boards

        result = kanban_list_boards()
        data = json.loads(result)
        assert data.get("success") is True
        assert "boards" in data

    def test_kanban_add_task(self):
        """测试 kanban_add_task 函数"""
        from tools.kanban_tool import kanban_create_board, kanban_add_task

        # 先创建看板
        board_result = kanban_create_board("Test Board")
        board_data = json.loads(board_result)
        board_id = board_data.get("board_id")

        result = kanban_add_task(
            board_id=board_id,
            title="Test Task",
            description="Test description",
            priority="high",
        )
        data = json.loads(result)
        assert data.get("success") is True
        assert "task_id" in data

    def test_kanban_view_board(self):
        """测试 kanban_view_board 函数"""
        from tools.kanban_tool import kanban_create_board, kanban_view_board

        board_result = kanban_create_board("View Test Board")
        board_data = json.loads(board_result)
        board_id = board_data.get("board_id")

        result = kanban_view_board(board_id)
        data = json.loads(result)
        assert data.get("success") is True
        assert "board" in data
        assert "columns" in data["board"]

    def test_kanban_create(self):
        """测试 kanban_create 函数"""
        from tools.kanban_tool import kanban_create

        result = kanban_create(title="Full Featured Task", priority=2, assignee="worker-1")
        data = json.loads(result)
        assert data.get("success") is True
        assert "task_id" in data

    def test_kanban_show(self):
        """测试 kanban_show 函数"""
        from tools.kanban_tool import kanban_create, kanban_show

        create_result = kanban_create(title="Show Test Task")
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        result = kanban_show(task_id)
        data = json.loads(result)
        assert data.get("success") is True
        assert "task" in data
        assert "comments" in data
        assert "events" in data

    def test_kanban_list(self):
        """测试 kanban_list 函数"""
        from tools.kanban_tool import kanban_list

        result = kanban_list()
        data = json.loads(result)
        assert data.get("success") is True
        assert "tasks" in data

    def test_kanban_list_with_status_filter(self):
        """测试 kanban_list 带状态筛选"""
        from tools.kanban_tool import kanban_list

        result = kanban_list(status="todo")
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_update(self):
        """测试 kanban_update 函数"""
        from tools.kanban_tool import kanban_create, kanban_update

        create_result = kanban_create(title="Update Test Task")
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        result = kanban_update(task_id, title="Updated Title", priority=2)
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_complete(self):
        """测试 kanban_complete 函数"""
        from tools.kanban_tool import kanban_create, kanban_complete

        create_result = kanban_create(
            title="Complete Test Task", initial_status="running"
        )
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        result = kanban_complete(task_id, summary="Task completed successfully")
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_block(self):
        """测试 kanban_block 函数"""
        from tools.kanban_tool import kanban_create, kanban_block

        create_result = kanban_create(
            title="Block Test Task", initial_status="running"
        )
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        result = kanban_block(task_id, reason="Need more info")
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_unblock(self):
        """测试 kanban_unblock 函数"""
        from tools.kanban_tool import kanban_create, kanban_block, kanban_unblock

        create_result = kanban_create(
            title="Unblock Test Task", initial_status="running"
        )
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        kanban_block(task_id, reason="Need more info")
        result = kanban_unblock(task_id)
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_comment(self):
        """测试 kanban_comment 函数"""
        from tools.kanban_tool import kanban_create, kanban_comment

        create_result = kanban_create(title="Comment Test Task")
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        result = kanban_comment(task_id, body="This is a test comment")
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_link(self):
        """测试 kanban_link 函数"""
        from tools.kanban_tool import kanban_create, kanban_link

        parent_result = kanban_create(title="Parent Task")
        parent_data = json.loads(parent_result)
        parent_id = parent_data.get("task_id")

        child_result = kanban_create(title="Child Task")
        child_data = json.loads(child_result)
        child_id = child_data.get("task_id")

        result = kanban_link(parent_id, child_id)
        data = json.loads(result)
        assert data.get("success") is True

    def test_kanban_delete(self):
        """测试 kanban_delete 函数"""
        from tools.kanban_tool import kanban_create, kanban_delete

        create_result = kanban_create(title="Delete Test Task")
        create_data = json.loads(create_result)
        task_id = create_data.get("task_id")

        result = kanban_delete(task_id)
        data = json.loads(result)
        assert data.get("success") is True


# =============================================================================
# TestEdgeCases - 边界情况测试
# =============================================================================


class TestEdgeCases:
    """测试边界情况"""

    def test_task_create_with_unicode(self, kanban_db):
        """测试创建带 Unicode 字符的任务"""
        from tools.kanban_db import board_create, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Unicode Board")
        task_id = task_create(conn, board.id, title="测试任务 🚀", body="描述包含中文和 emoji")
        task = task_get(conn, task_id)
        assert task.title == "测试任务 🚀"
        assert task.body == "描述包含中文和 emoji"
        conn.close()

    def test_task_create_with_long_body(self, kanban_db):
        """测试创建带长描述的任务"""
        from tools.kanban_db import board_create, task_create, task_get

        conn = kanban_db.connect()
        board = board_create(conn, name="Long Body Board")
        long_body = "A" * 10000
        task_id = task_create(conn, board.id, title="Long Body Task", body=long_body)
        task = task_get(conn, task_id)
        assert len(task.body) == 10000
        conn.close()

    def test_task_list_with_limit(self, kanban_db):
        """测试限制返回数量"""
        from tools.kanban_db import board_create, task_create, task_list

        conn = kanban_db.connect()
        board = board_create(conn, name="Limit Board")
        for i in range(20):
            task_create(conn, board.id, title=f"Task {i}")

        tasks = task_list(conn, limit=5)
        assert len(tasks) == 5
        conn.close()

    def test_board_delete_nonexistent(self, kanban_db):
        """测试删除不存在的看板"""
        from tools.kanban_db import board_delete

        conn = kanban_db.connect()
        result = board_delete(conn, "non-existent-id")
        assert result is False
        conn.close()

    def test_task_delete_nonexistent(self, kanban_db):
        """测试删除不存在的任务"""
        from tools.kanban_db import task_delete

        conn = kanban_db.connect()
        result = task_delete(conn, "non-existent-id")
        assert result is False
        conn.close()


# =============================================================================
# 运行测试
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
