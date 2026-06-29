#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SessionTodoStore 单元测试

测试 SessionTodoStore 的核心功能，包括状态映射和持久化。
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


class TestSessionTodoStoreBasic:
    """测试 SessionTodoStore 基本功能"""

    def test_session_todo_store_creation(self):
        """测试 SessionTodoStore 创建"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        assert store._items == []
        assert store._kanban_manager is None

    def test_write_single_todo(self):
        """测试写入单个 todo"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        todos = [{"id": "1", "content": "Task 1", "status": "pending"}]
        result = store.write(todos)
        assert len(result) == 1
        assert result[0]["id"] == "1"
        assert result[0]["content"] == "Task 1"
        assert result[0]["status"] == "pending"

    def test_write_multiple_todos(self):
        """测试写入多个 todos"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "in_progress"},
            {"id": "3", "content": "Task 3", "status": "completed"},
        ]
        result = store.write(todos)
        assert len(result) == 3

    def test_read_empty_store(self):
        """测试读取空 store"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        result = store.read()
        assert result == []

    def test_has_items(self):
        """测试 has_items 方法"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        assert store.has_items() is False
        store.write([{"id": "1", "content": "Task", "status": "pending"}])
        assert store.has_items() is True

    def test_merge_mode(self):
        """测试 merge 模式"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        store.write([{"id": "1", "content": "Task 1", "status": "pending"}])
        store.write([{"id": "2", "content": "Task 2", "status": "pending"}], merge=True)
        result = store.read()
        assert len(result) == 2

    def test_replace_mode(self):
        """测试 replace 模式"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        store.write([{"id": "1", "content": "Task 1", "status": "pending"}])
        store.write([{"id": "2", "content": "Task 2", "status": "pending"}])
        result = store.read()
        assert len(result) == 1
        assert result[0]["id"] == "2"

    def test_validate_todo(self):
        """测试 todo 验证"""
        from tools.todo_tool import SessionTodoStore
        # 无效状态转为 pending
        item = SessionTodoStore._validate({"id": "1", "content": "Task", "status": "invalid"})
        assert item["status"] == "pending"
        # 空 id 使用 "?"
        item = SessionTodoStore._validate({"content": "Task"})
        assert item["id"] == "?"
        # 空 content 使用默认值
        item = SessionTodoStore._validate({"id": "1"})
        assert item["content"] == "(no description)"

    def test_dedupe_by_id(self):
        """测试按 id 去重"""
        from tools.todo_tool import SessionTodoStore
        todos = [
            {"id": "1", "content": "First"},
            {"id": "2", "content": "Second"},
            {"id": "1", "content": "Updated"},
        ]
        result = SessionTodoStore._dedupe_by_id(todos)
        assert len(result) == 2
        # 保留按原始顺序的第一个出现，但内容是最后一次的值
        # 结果顺序：id=2 在 index 1，id=1 在 index 2（最后一次出现）
        assert result[0]["id"] == "2"
        assert result[1]["id"] == "1"
        assert result[1]["content"] == "Updated"


class TestSessionTodoStoreStatusMapping:
    """测试状态映射功能"""

    def test_todo_to_kanban_mapping(self):
        """测试 Todo → Kanban 状态映射"""
        from tools.todo_tool import SessionTodoStore, TODO_TO_KANBAN_STATUS

        assert SessionTodoStore.map_todo_to_kanban_status("pending") == "todo"
        assert SessionTodoStore.map_todo_to_kanban_status("in_progress") == "running"
        assert SessionTodoStore.map_todo_to_kanban_status("completed") == "done"
        assert SessionTodoStore.map_todo_to_kanban_status("cancelled") == "done"
        # 未知状态默认为 todo
        assert SessionTodoStore.map_todo_to_kanban_status("unknown") == "todo"

    def test_kanban_to_todo_mapping(self):
        """测试 Kanban → Todo 状态映射"""
        from tools.todo_tool import SessionTodoStore, KANBAN_TO_TODO_STATUS

        assert SessionTodoStore.map_kanban_to_todo_status("triage") == "pending"
        assert SessionTodoStore.map_kanban_to_todo_status("todo") == "pending"
        assert SessionTodoStore.map_kanban_to_todo_status("ready") == "pending"
        assert SessionTodoStore.map_kanban_to_todo_status("running") == "in_progress"
        assert SessionTodoStore.map_kanban_to_todo_status("done") == "completed"
        assert SessionTodoStore.map_kanban_to_todo_status("blocked") == "in_progress"
        # 未知状态默认为 pending
        assert SessionTodoStore.map_kanban_to_todo_status("unknown") == "pending"


class TestSessionTodoStorePersistence:
    """测试 SessionTodoStore 持久化功能"""

    def test_set_kanban_manager(self):
        """测试设置 KanbanManager"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        mock_kanban = Mock()
        store.set_kanban_manager(mock_kanban)
        assert store._kanban_manager is mock_kanban

    def test_init_with_kanban_manager(self):
        """测试初始化时传入 KanbanManager"""
        from tools.todo_tool import SessionTodoStore
        mock_kanban = Mock()
        store = SessionTodoStore(kanban_manager=mock_kanban)
        assert store._kanban_manager is mock_kanban

    def test_write_without_persist(self):
        """测试不持久化时 Kanban 不被调用"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        mock_kanban = Mock()
        store.set_kanban_manager(mock_kanban)

        store.write([{"id": "1", "content": "Task", "status": "pending"}], persist=False)

        mock_kanban.get_default_board_id.assert_not_called()
        mock_kanban.create_task.assert_not_called()

    def test_write_with_persist_creates_task(self):
        """测试持久化时创建 Kanban Task"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        mock_kanban = Mock()
        mock_kanban.get_default_board_id.return_value = "board_1"
        mock_kanban.create_task.return_value = "kanban_task_1"
        store.set_kanban_manager(mock_kanban)

        todos = [{"id": "1", "content": "Task 1", "status": "pending"}]
        store.write(todos, persist=True)

        mock_kanban.get_default_board_id.assert_called_once()
        mock_kanban.create_task.assert_called_once()
        call_kwargs = mock_kanban.create_task.call_args[1]
        assert call_kwargs["board_id"] == "board_1"
        assert call_kwargs["title"] == "Task 1"
        assert call_kwargs["status"] == "todo"

    def test_write_with_persist_updates_existing_task(self):
        """测试持久化时更新已存在的 Kanban Task"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        mock_kanban = Mock()
        mock_kanban.get_default_board_id.return_value = "board_1"
        mock_kanban.create_task.return_value = "kanban_task_1"
        store.set_kanban_manager(mock_kanban)

        # 第一次写入创建
        todos1 = [{"id": "1", "content": "Task 1", "status": "pending"}]
        store.write(todos1, persist=True)

        # 第二次写入更新
        mock_kanban.reset_mock()
        todos2 = [{"id": "1", "content": "Task 1 Updated", "status": "in_progress"}]
        store.write(todos2, persist=True)

        mock_kanban.update_task.assert_called_once()
        # update_task 的第一个参数是位置参数 task_id
        call_args = mock_kanban.update_task.call_args[0]
        call_kwargs = mock_kanban.update_task.call_args[1]
        assert call_args[0] == "kanban_task_1"  # task_id
        assert call_kwargs["title"] == "Task 1 Updated"
        assert call_kwargs["status"] == "running"

    def test_persist_handles_kanban_error(self):
        """测试持久化失败不影响主流程"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        mock_kanban = Mock()
        mock_kanban.get_default_board_id.side_effect = Exception("DB Error")
        store.set_kanban_manager(mock_kanban)

        # 不应抛出异常
        todos = [{"id": "1", "content": "Task", "status": "pending"}]
        result = store.write(todos, persist=True)

        # 但内存中仍然保存
        assert len(result) == 1


class TestTodoToolFunction:
    """测试 todo_tool 函数"""

    def test_todo_tool_without_store(self):
        """测试无 store 时返回错误"""
        from tools.todo_tool import todo_tool
        result = todo_tool()
        data = json.loads(result)
        assert data["success"] is False
        assert "error" in data

    def test_todo_tool_read(self):
        """测试读取 todo"""
        from tools.todo_tool import SessionTodoStore, todo_tool
        store = SessionTodoStore()
        store.write([{"id": "1", "content": "Task", "status": "pending"}])

        result = todo_tool(store=store)
        data = json.loads(result)
        # todo_tool 不返回 success 字段，直接返回 todos 和 summary
        assert "todos" in data
        assert len(data["todos"]) == 1
        assert data["summary"]["total"] == 1

    def test_todo_tool_write(self):
        """测试写入 todo"""
        from tools.todo_tool import SessionTodoStore, todo_tool
        store = SessionTodoStore()

        todos = [{"id": "1", "content": "Task", "status": "pending"}]
        result = todo_tool(todos=todos, store=store)
        data = json.loads(result)

        assert "summary" in data
        assert data["summary"]["total"] == 1
        assert data["summary"]["pending"] == 1

    def test_todo_tool_with_persist(self):
        """测试带持久化的 todo"""
        from tools.todo_tool import SessionTodoStore, todo_tool
        store = SessionTodoStore()
        mock_kanban = Mock()
        mock_kanban.get_default_board_id.return_value = "board_1"
        mock_kanban.create_task.return_value = "task_1"
        store.set_kanban_manager(mock_kanban)

        todos = [{"id": "1", "content": "Task", "status": "pending"}]
        result = todo_tool(todos=todos, store=store, persist=True)

        mock_kanban.create_task.assert_called_once()


class TestFormatForInjection:
    """测试 format_for_injection 方法"""

    def test_format_empty_store(self):
        """测试空 store 返回 None"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        assert store.format_for_injection() is None

    def test_format_completed_tasks_only(self):
        """测试只有已完成任务时返回 None"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        store.write([{"id": "1", "content": "Task", "status": "completed"}])
        assert store.format_for_injection() is None

    def test_format_with_pending_tasks(self):
        """测试格式化待处理任务"""
        from tools.todo_tool import SessionTodoStore
        store = SessionTodoStore()
        store.write([
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "in_progress"},
            {"id": "3", "content": "Task 3", "status": "completed"},
        ])
        result = store.format_for_injection()
        assert result is not None
        assert "[ ]" in result  # pending
        assert "[>]" in result   # in_progress
        assert "[x]" not in result  # completed 不显示
        assert "Task 1" in result
        assert "Task 2" in result
        assert "Task 3" not in result  # completed 不显示