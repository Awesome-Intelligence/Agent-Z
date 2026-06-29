"""
TUI 侧边栏组件 - 提供文件树、任务、Goal、Agent、日志面板
使用 Textual TabbedContent + TabPane 组件实现
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Iterable
from typing_extensions import Self

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Click
from textual.message import Message
from textual.widgets import Static, Log, TabbedContent, TabPane, DirectoryTree
from textual.widgets import Tabs
from textual import on

# 文件预览支持
try:
    from tui.views.file_preview import FilePreviewScreen
except ImportError:
    FilePreviewScreen = None


# 图标系统
try:
    from tui.theming import (
        FILE_TYPE_ICONS,
        get_file_icon,
        TASK_STATUS_ICONS,
        AGENT_STATUS_ICONS,
        LOG_LEVEL_ICONS,
        PANEL_ICONS,
    )
except ImportError:
    # 降级方案：使用内联默认值
    FILE_TYPE_ICONS = {".default": "📄"}
    TASK_STATUS_ICONS = {}
    AGENT_STATUS_ICONS = {"idle": "🟢", "busy": "🟠"}
    LOG_LEVEL_ICONS = {"INFO": "ℹ️", "DEBUG": "🐛", "WARNING": "⚠️", "ERROR": "❌"}
    PANEL_ICONS = {"file_tree": "📁", "tasks": "📋", "goal": "🎯", "agent": "🤖", "logs": "📜"}

    def get_file_icon(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return FILE_TYPE_ICONS.get(ext, FILE_TYPE_ICONS[".default"])


# ============================================================================
# 过滤目录树
# ============================================================================


class FilteredDirectoryTree(DirectoryTree):
    """过滤后的目录树组件."""

    BLOCKLIST = {".venv", "node_modules", "__pycache__", ".git", ".idea", ".vscode"}

    def filter_paths(self, paths: Iterable[Path]) -> list[Path]:
        """过滤目录树，隐藏隐藏文件和黑名单目录."""
        result = []
        for path in paths:
            if not path.name.startswith(".") and path.name not in self.BLOCKLIST:
                result.append(path)
        return result


# ============================================================================
# 面板基类
# ============================================================================


class SidebarPane(TabPane):
    """侧边栏面板基类."""

    DEFAULT_CSS = """
    SidebarPane {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    """

    def set_focus_within(self) -> None:
        """设置面板内部焦点（可被子类重写）."""

    def activate(self) -> Self:
        """激活面板并切换到该 Tab."""
        assert self.parent is not None
        if self.id is not None and isinstance(self.parent.parent, TabbedContent):
            self.parent.parent.active = self.id
        return self


# ============================================================================
# Goal 面板
# ============================================================================


class GoalPane(SidebarPane):
    """
    Goal 面板 - 实时显示当前 Goal 的状态
    
    功能:
    1. 显示 Goal 状态（活跃/暂停/完成/过期/清除）
    2. 显示目标描述
    3. 显示剩余轮次和迭代进度
    4. 支持通过 GoalManager 动态更新
    """
    
    # Goal 状态图标
    STATUS_ICONS = {
        "active": "🎯",
        "paused": "⏸️",
        "done": "✅",
        "cleared": "🗑️",
        "expired": "⏰",
    }
    
    # 默认 CSS
    DEFAULT_CSS = """
    GoalPane {
        width: 100%;
        height: 100%;
    }
    
    GoalPane #goal-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    GoalPane #goal-header {
        width: 100%;
        padding: 1;
        background: $accent 15%;
        border: solid $accent;
        margin-bottom: 1;
    }
    
    GoalPane #goal-progress {
        width: 100%;
        padding: 1;
    }
    
    GoalPane #goal-empty {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }
    
    GoalPane .status-badge {
        padding: 0 1;
    }
    
    GoalPane .status-badge.active {
        color: $success;
        text-style: bold;
    }
    
    GoalPane .status-badge.paused {
        color: $warning;
        text-style: bold;
    }
    
    GoalPane .status-badge.done {
        color: $success;
    }
    
    GoalPane .status-badge.expired {
        color: $error;
    }
    
    GoalPane .status-badge.cleared {
        color: $text-muted;
    }
    
    GoalPane #goal-detail {
        padding: 1;
        color: $text-muted;
    }
    """
    
    def __init__(self, goal_manager=None) -> None:
        self._goal_manager = goal_manager
        self._refresh_interval: float = 1.0  # 刷新间隔（秒）
        self._logger = None
        super().__init__(id="goal", title="Goal")
    
    def set_goal_manager(self, goal_manager) -> None:
        """设置 GoalManager 实例"""
        self._goal_manager = goal_manager
    
    def compose(self) -> ComposeResult:
        """组合子组件."""
        with Vertical(id="goal-container"):
            # Goal 头部（状态+目标描述）
            yield Static("", id="goal-header")
            # 进度条
            yield Static("", id="goal-progress")
            # 详细状态
            yield Static("", id="goal-detail")
            # 空状态提示
            yield Static("[dim]暂无活跃的 Goal[/dim]\n\n使用 /goal <目标> 创建新 Goal", id="goal-empty")
    
    def on_mount(self) -> None:
        """组件挂载时初始化."""
        try:
            from common.logging_manager import get_tui_logger
            self._logger = get_tui_logger("GoalPane")
        except ImportError:
            self._logger = None
        
        # 启动定时刷新
        self._start_refresh_timer()
    
    def _start_refresh_timer(self) -> None:
        """启动定时刷新定时器"""
        self.set_interval(self._refresh_interval, self._refresh_goal)
        self._refresh_goal()  # 立即刷新一次
    
    def _refresh_goal(self) -> None:
        """从 GoalManager 刷新 Goal 状态"""
        if not self._goal_manager:
            self._show_empty_state()
            return
        
        try:
            goal_state = self._goal_manager._current_goal
            
            if not goal_state:
                self._show_empty_state()
                return
            
            # 更新显示
            self._update_display(goal_state)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to refresh Goal state: {e}")
            self._show_empty_state()
    
    def _show_empty_state(self) -> None:
        """显示空状态"""
        try:
            header = self.query_one("#goal-header", Static)
            progress = self.query_one("#goal-progress", Static)
            detail = self.query_one("#goal-detail", Static)
            empty = self.query_one("#goal-empty", Static)
            
            header.update("")
            progress.update("")
            detail.update("")
            empty.display = True
        except Exception:
            pass
    
    def _update_display(self, goal_state) -> None:
        """更新 Goal 状态显示"""
        try:
            header = self.query_one("#goal-header", Static)
            progress = self.query_one("#goal-progress", Static)
            detail = self.query_one("#goal-detail", Static)
            empty = self.query_one("#goal-empty", Static)
            
            empty.display = False
            
            # 获取状态信息
            status = goal_state.status
            status_icon = self.STATUS_ICONS.get(status, "❓")
            status_text = self._get_status_text(status)
            
            # 获取目标描述（截断过长文本）
            goal_text = goal_state.goal
            display_goal = goal_text[:60] + "..." if len(goal_text) > 60 else goal_text
            
            # 获取进度信息
            budget = self._goal_manager._budget
            current_turn = budget.turns_used
            max_turns = budget.max_turns
            remaining_turns = budget.remaining_turns()
            turn_progress = int((current_turn / max_turns) * 100) if max_turns > 0 else 0
            
            # 更新头部
            header.update(f"""[bold]{status_icon} {status_text}[/bold]

[accent]{display_goal}[/accent]""")
            
            # 更新进度条
            progress_bar = self._make_progress_bar(turn_progress)
            progress.update(f"""[dim]轮次进度:[/dim] {current_turn}/{max_turns}
{progress_bar} {turn_progress}% | 剩余 {remaining_turns} 轮""")
            
            # 更新详细信息
            detail_lines = []
            
            # 迭代信息
            if budget:
                detail_lines.append(f"[dim]迭代:[/dim] {budget.used}/{budget.max_iterations}")
            
            # Judge 判决信息
            if goal_state.last_verdict is not None:
                verdict_icon = "✅" if goal_state.last_verdict else "🔄"
                detail_lines.append(f"[dim]上次判决:[/dim] {verdict_icon} {'完成' if goal_state.last_verdict else '继续'}")
                if goal_state.last_reason:
                    reason = goal_state.last_reason[:40] + "..." if len(goal_state.last_reason) > 40 else goal_state.last_reason
                    detail_lines.append(f"  {reason}")
            
            # Subgoals 数量
            if goal_state.subgoals:
                detail_lines.append(f"[dim]子目标:[/dim] {len(goal_state.subgoals)} 个")
            
            # 暂停原因
            if status == "paused" and goal_state.paused_reason:
                paused = goal_state.paused_reason[:50] + "..." if len(goal_state.paused_reason) > 50 else goal_state.paused_reason
                detail_lines.append(f"[dim]暂停原因:[/dim] {paused}")
            
            detail.update("\n".join(detail_lines) if detail_lines else "[dim]无详细信息[/dim]")
            
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to update Goal display: {e}")
    
    def _get_status_text(self, status: str) -> str:
        """获取状态的中文文本"""
        status_map = {
            "active": "执行中",
            "paused": "已暂停",
            "done": "已完成",
            "cleared": "已清除",
            "expired": "已过期",
        }
        return status_map.get(status, status)
    
    def _make_progress_bar(self, percent: int, width: int = 12) -> str:
        """生成进度条"""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[success]{'█' * filled}[/success][dim]{'░' * empty}[/dim]"


# ============================================================================
# 任务面板
# ============================================================================


class TasksPane(SidebarPane):
    """
    任务面板 - 实时显示当前会话的 Todo 任务
    
    功能:
    1. 直接从 SessionTodoStore 读取任务状态（Layer 1）
    2. 定期刷新任务列表
    3. 显示任务状态和进度
    4. 会话结束自动清除（符合 Layer 1 设计）
    """
    
    # 内部数据结构
    _tasks: Dict[str, List] = {}  # task_id -> subtasks
    _current_task_id: Optional[str] = None
    _current_subtask_id: Optional[int] = None
    _progress_percent: int = 0
    _expanded_tasks: set = set()  # 展开的任务 ID
    _todo_store = None  # SessionTodoStore 实例
    _refresh_interval: float = 1.0  # 刷新间隔（秒）
    
    # 状态图标（映射 todo 状态到图标）
    STATUS_ICONS = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
        "cancelled": "➖",
    }
    
    # 默认 CSS
    DEFAULT_CSS = """
    TasksPane {
        width: 100%;
        height: 100%;
    }
    
    TasksPane #tasks-container {
        width: 100%;
        height: 100%;
        padding: 0;
    }
    
    TasksPane #current-task {
        width: 100%;
        padding: 0 1;
        background: $accent 15%;
        border: solid $accent;
        margin-bottom: 1;
    }
    
    TasksPane .task-item {
        padding: 0 1 0 2;
    }
    
    TasksPane .task-item.pending {
        color: $text-muted;
    }
    
    TasksPane .task-item.running {
        color: $accent;
        text-style: bold;
    }
    
    TasksPane .task-item.completed {
        color: $success;
    }
    
    TasksPane .task-item.failed,
    TasksPane .task-item.error {
        color: $error;
    }
    
    TasksPane .task-item.cancelled {
        color: $text-muted;
        text-style: italic;
    }
    
    TasksPane #empty-state {
        color: $text-muted;
        text-style: italic;
    }
    """
    
    def __init__(self) -> None:
        super().__init__(id="tasks", title="任务")
        self._has_messages = False  # 暂时禁用旧消息机制，使用 Kanban 直读
        self._logger = None
    
    def compose(self) -> ComposeResult:
        """组合子组件."""
        with Vertical(id="tasks-container"):
            # 当前执行任务（动态显示）
            yield Static("", id="current-task")
            
            # 任务列表
            yield Static("[dim]暂无任务[/dim]", id="tasks-list")
    
    def on_mount(self) -> None:
        """组件挂载时初始化."""
        # 先初始化 logger
        try:
            from common.logging_manager import get_tui_logger
            self._logger = get_tui_logger("TasksPane")
        except ImportError:
            self._logger = None
        
        # 初始化 SessionTodoStore
        self._init_todo_store()
        
        # 启动定时刷新
        self._start_refresh_timer()
    
    def _init_todo_store(self) -> None:
        """初始化 SessionTodoStore"""
        try:
            from tools.todo_tool import get_session_todo_store
            self._todo_store = get_session_todo_store()
            if self._logger:
                self._logger.debug("SessionTodoStore initialized")
        except ImportError as e:
            if self._logger:
                self._logger.warning(f"Failed to init SessionTodoStore: {e}")
            self._todo_store = None
    
    def _start_refresh_timer(self) -> None:
        """启动定时刷新定时器"""
        self.set_interval(self._refresh_interval, self._refresh_tasks)
        self._refresh_tasks()  # 立即刷新一次
    
    def _refresh_tasks(self) -> None:
        """从 SessionTodoStore 刷新任务列表（Layer 1 - 当前会话）"""
        if self._todo_store is None:
            return
        
        try:
            # 直接从 SessionTodoStore 读取任务
            todos = self._todo_store.read()
            
            if not todos:
                self._tasks = {}
                self._update_display()
                return
            
            # 转换为 TasksPane 内部格式
            self._tasks = {"session": self._convert_todos(todos)}
            
            # 找出当前进行中的任务
            in_progress = [t for t in todos if t.get("status") == "in_progress"]
            if in_progress:
                self._current_task_id = in_progress[0].get("id")
                self._update_current_task_display(in_progress[0])
            
            self._update_display()
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to refresh tasks from SessionTodoStore: {e}")
    
    def _convert_todos(self, todos: List[Dict]) -> List:
        """将 Todo 项转换为 TasksPane 内部格式
        
        Args:
            todos: SessionTodoStore 返回的任务列表
            
        Returns:
            List: 转换后的任务列表
        """
        converted = []
        
        for todo in todos:
            # 创建简化的任务项
            task_item = type('TodoItem', (), {
                'task_id': todo.get("id", ""),
                'subtask_id': todo.get("id", ""),
                'title': todo.get("content", ""),
                'description': '',
                'status': todo.get("status", "pending"),
                'progress': self._get_todo_progress(todo.get("status", "pending")),
            })()
            converted.append(task_item)
        
        return converted
    
    def _get_todo_progress(self, todo_status: str) -> int:
        """获取 Todo 任务进度"""
        progress_map = {
            "pending": 0,
            "in_progress": 50,
            "completed": 100,
            "cancelled": 100,
        }
        return progress_map.get(todo_status, 0)
    
    def _update_current_task_display(self, todo: Dict) -> None:
        """更新当前执行任务显示"""
        try:
            current_task_widget = self.query_one("#current-task", Static)
            
            status_icon = self.STATUS_ICONS.get("in_progress", "🔄")
            title = todo.get("content", "")[:40] if len(todo.get("content", "")) > 40 else todo.get("content", "")
            
            # 格式化状态文本
            status_text = self._get_status_text("in_progress")
            progress_bar = self._make_progress_bar(50)
            
            current_task_widget.update(f"""[bold]{status_icon} {status_text}[/bold]
 
 [accent]{title}[/accent]
 
 {progress_bar} 50%
 """)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to update current task display: {e}")
    
    def _get_status_text(self, status: str) -> str:
        """获取状态的中文文本"""
        status_map = {
            "triage": "待分类",
            "todo": "待处理",
            "ready": "准备就绪",
            "pending": "待处理",
            "running": "执行中",
            "blocked": "已阻塞",
            "done": "已完成",
            "completed": "已完成",
            "failed": "已失败",
            "error": "错误",
            "cancelled": "已取消",
            "archived": "已归档",
            "timed_out": "已超时",
        }
        return status_map.get(status, status)
    
    # ==================== 保留旧消息处理（兼容性） ====================
    
    def on_tasks_pane_updated(self, event) -> None:
        """处理任务面板更新消息（保留兼容性）"""
        # 如果收到外部消息，也触发刷新以保持同步
        self._refresh_tasks()
    
    def on_current_task_changed(self, event) -> None:
        """处理当前任务变更消息（保留兼容性）"""
        # 收到消息时也触发刷新
        self._refresh_tasks()
    
    # ==================== 显示逻辑 ====================
    
    def _update_display(self) -> None:
        """更新任务列表显示"""
        tasks_list_widget = self.query_one("#tasks-list", Static)
        
        if not self._tasks:
            tasks_list_widget.update("[dim]暂无任务[/dim]")
            return
        
        lines = []
        
        # 按状态分类收集所有任务（只支持 todo 的四种状态）
        status_groups: Dict[str, List] = {
            "in_progress": [],
            "pending": [],
            "completed": [],
            "cancelled": [],
        }
        
        for board_id, subtasks in self._tasks.items():
            for subtask in subtasks:
                status = getattr(subtask, 'status', 'unknown')
                
                if status == "in_progress":
                    status_groups["in_progress"].append(subtask)
                elif status == "pending":
                    status_groups["pending"].append(subtask)
                elif status == "completed":
                    status_groups["completed"].append(subtask)
                elif status == "cancelled":
                    status_groups["cancelled"].append(subtask)
        
        # 按状态分组显示
        status_order = ["in_progress", "pending", "cancelled", "completed"]
        status_labels = {
            "in_progress": "🔄 进行中",
            "pending": "⏳ 待处理",
            "completed": "✅ 已完成",
            "cancelled": "➖ 已取消",
        }
        
        has_tasks = False
        for status_key in status_order:
            tasks = status_groups[status_key]
            if not tasks:
                continue
            
            has_tasks = True
            lines.append(f"[dim]{status_labels.get(status_key, status_key)}[/dim]")
            
            for subtask in tasks[:10]:  # 限制每组最多显示10个
                icon = self.STATUS_ICONS.get(
                    getattr(subtask, 'status', 'unknown'),
                    "❓"
                )
                
                title = getattr(subtask, 'title', '未知任务')
                display_title = title[:38] if len(title) > 38 else title
                
                progress = getattr(subtask, 'progress', 0)
                if progress > 0 and progress < 100:
                    progress_bar = self._make_progress_bar(progress)
                    lines.append(f"  {icon} {display_title} {progress_bar}")
                else:
                    lines.append(f"  {icon} {display_title}")
            
            if len(tasks) > 10:
                lines.append(f"  [dim]... 还有 {len(tasks) - 10} 个任务[/dim]")
            
            lines.append("")  # 组之间空行
        
        if not has_tasks:
            lines.append("[dim]暂无任务[/dim]")
        
        tasks_list_widget.update("\n".join(lines).strip())
    
    def _format_current_task(self, title: str) -> str:
        """格式化当前执行任务"""
        progress_bar = self._make_progress_bar(self._progress_percent)
        icon = self.STATUS_ICONS.get("running", "🔄")
        
        return f"""[bold]{icon} 执行中[/bold]

[accent]{title or "未知任务"}[/accent]

{progress_bar} {self._progress_percent}%
"""
    
    def _make_progress_bar(self, percent: int, width: int = 10) -> str:
        """生成进度条"""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[success]{'█' * filled}[/success][dim]{'░' * empty}[/dim]"
    
    # ==================== 交互操作 ====================
    
    def toggle_task_expanded(self, task_id: str) -> None:
        """切换任务展开/折叠"""
        if task_id in self._expanded_tasks:
            self._expanded_tasks.discard(task_id)
        else:
            self._expanded_tasks.add(task_id)
        self._update_display()


# ============================================================================
# 文件树面板
# ============================================================================


class FileTreePane(SidebarPane):
    """可交互的文件树面板."""

    class FileSelected(Message):
        """文件选中消息."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    DEFAULT_CSS = """
    FileTreePane {
        width: 100%;
        height: 100%;
    }

    FileTreePane DirectoryTree {
        height: 100%;
        background: transparent;
    }

    FileTreePane DirectoryTree > .tree--cursor {
        background: $accent 25%;
        color: $text;
    }

    FileTreePane DirectoryTree .tree--node-toggle {
        color: $accent;
    }
    """

    def __init__(self, cwd: str = None) -> None:
        self._cwd = Path(cwd) if cwd else Path.cwd()
        super().__init__(id="file_tree", title="文件")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield FilteredDirectoryTree(
            self._cwd,
            id="file-tree-widget",
        )

    @on(DirectoryTree.FileSelected)
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """处理文件选中事件."""
        event.stop()
        file_path = Path(event.path)
        
        # 如果是目录，展开/折叠
        if file_path.is_dir():
            return
        
        # 如果是文件，打开预览
        if FilePreviewScreen:
            self.app.push_screen(FilePreviewScreen(file_path))

    def set_focus_within(self) -> None:
        """设置面板内部焦点."""
        tree = self.query_one(DirectoryTree, None)
        if tree:
            tree.focus(scroll_visible=False)


# ============================================================================
# Agent 面板
# ============================================================================


class AgentPane(SidebarPane):
    """Agent 面板."""

    def __init__(self, agent=None) -> None:
        self._agent = agent
        super().__init__(id="agent", title="Agent")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        idle_icon = AGENT_STATUS_ICONS.get("idle", "🟢")
        yield Static(f"[green]{idle_icon} 空闲[/green]", id="agent-content")


# ============================================================================
# 日志面板
# ============================================================================


class LogsPane(SidebarPane):
    """日志面板."""

    def __init__(self) -> None:
        super().__init__(id="logs", title="日志")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield Log(id="log-output", auto_scroll=True, max_lines=1000, highlight=True)


# ============================================================================
# 侧边栏容器
# ============================================================================


class SidebarContainer(Vertical, can_focus=False, can_focus_children=True):
    """侧边栏主容器."""

    DEFAULT_CSS = """
    SidebarContainer {
        width: 100%;
        height: 100%;
    }

    SidebarContainer > TabbedContent {
        height: 100%;
    }

    SidebarContainer Tabs {
        dock: top;
    }

    SidebarContainer Tabs Tab {
        color: $text-muted;
    }

    SidebarContainer Tabs Tab:hover {
        background: transparent;
        color: $text;
    }

    SidebarContainer Tabs Tab.active {
        background: transparent;
        color: $accent;
        text-style: bold;
        border-bottom: solid $accent;
    }

    SidebarContainer ContentSwitcher {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+left", "previous_tab", "Previous tab", show=False),
        Binding("ctrl+right", "next_tab", "Next tab", show=False),
    ]

    def __init__(self, cwd: str = None, agent=None, goal_manager=None):
        super().__init__(id="sidebar-container-inner")
        self._cwd = cwd
        self._agent = agent
        self._goal_manager = goal_manager

    def compose(self) -> ComposeResult:
        """组合子组件."""
        # 创建面板实例
        self._tasks_pane = TasksPane()
        self._goal_pane = GoalPane(self._goal_manager)
        self._file_tree_pane = FileTreePane(self._cwd)
        self._agent_pane = AgentPane(self._agent)
        self._logs_pane = LogsPane()

        with TabbedContent():
            yield self._tasks_pane
            yield self._goal_pane
            yield self._file_tree_pane
            yield self._agent_pane
            yield self._logs_pane

    @property
    def tasks_pane(self) -> TasksPane:
        """任务面板."""
        return self._tasks_pane
    
    @property
    def goal_pane(self) -> GoalPane:
        """Goal 面板."""
        return self._goal_pane

    @property
    def file_tree_pane(self) -> FileTreePane:
        """文件树面板."""
        return self._file_tree_pane

    @property
    def agent_pane(self) -> AgentPane:
        """Agent 面板."""
        return self._agent_pane

    @property
    def logs_pane(self) -> LogsPane:
        """日志面板."""
        return self._logs_pane

    def switch_to_panel(self, panel_id: str) -> None:
        """切换到指定面板.

        Args:
            panel_id: 面板 ID (tasks, goal, file_tree, agent, logs)
        """
        tabs = self.query_one(Tabs)
        if panel_id in ["tasks", "goal", "file_tree", "agent", "logs"]:
            tabs.active = panel_id

    def set_goal_manager(self, goal_manager) -> None:
        """设置 GoalManager 实例并更新 Goal 面板"""
        self._goal_manager = goal_manager
        if self._goal_pane:
            self._goal_pane.set_goal_manager(goal_manager)

    @on(Tabs.TabActivated)
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Tab 切换时更新颜色."""
        # 获取当前主题颜色（从父组件或默认值）
        active_color = getattr(self, '_active_tab_color', '#B180D7')
        self.update_tab_colors(active_color)

    def set_active_color(self, color: str) -> None:
        """设置激活 Tab 的颜色.

        Args:
            color: 颜色值（十六进制）
        """
        self._active_tab_color = color
        self.update_tab_colors(color)

    def action_previous_tab(self) -> None:
        """切换到上一个 Tab."""
        tabs = self.query_one(Tabs)
        tabs.action_previous_tab()
        self.focus_active_tab()

    def action_next_tab(self) -> None:
        """切换到下一个 Tab."""
        tabs = self.query_one(Tabs)
        tabs.action_next_tab()
        self.focus_active_tab()

    def focus_active_tab(self) -> None:
        """聚焦当前激活的 Tab 内容."""
        if active := self.query_one(Tabs).active:
            self.query_one(f"SidebarPane#{active}", SidebarPane).set_focus_within()

    def update_tab_colors(self, active_color: str) -> None:
        """更新侧边栏 Tab 颜色.

        Args:
            active_color: 激活状态的 Tab 颜色（十六进制）
        """
        tabs = self.query_one(Tabs)
        for tab in tabs.query("Tab"):
            if tab.id == tabs.active:
                tab.styles.color = active_color
                tab.styles.border_bottom = f"solid {active_color}"
            else:
                tab.styles.color = ""
                tab.styles.border_bottom = ""


# ============================================================================
# 保留的辅助类（用于向后兼容）
# ============================================================================


class SidebarTabBar(Static):
    """侧边栏标签栏（已弃用，保留用于兼容）."""

    def __init__(self, on_switch: callable = None):
        super().__init__()
        self._on_switch = on_switch

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield Static("[dim]请使用 TabbedContent 切换面板[/dim]", id="deprecated-tabbar")


# ============================================================================
# 日志格式化辅助函数
# ============================================================================


def get_log_level_icon(level: str) -> str:
    """根据日志级别获取图标.

    Args:
        level: 日志级别字符串

    Returns:
        对应的 Emoji 图标
    """
    return LOG_LEVEL_ICONS.get(level.upper(), "ℹ️")


def format_log_entry(level: str, message: str) -> str:
    """格式化带图标的日志条目.

    Args:
        level: 日志级别
        message: 日志消息

    Returns:
        格式化的日志字符串
    """
    icon = get_log_level_icon(level)
    return f"{icon} [{level}]  {message}"


# ============================================================================
# 任务格式化辅助函数
# ============================================================================


def get_task_status_icon(status: str) -> str:
    """根据任务状态获取图标.

    Args:
        status: 任务状态字符串

    Returns:
        对应的 Emoji 图标
    """
    return TASK_STATUS_ICONS.get(status.lower(), "📋")


def format_task_item(title: str, status: str = "todo", priority: str = "normal") -> str:
    """格式化带图标的任务项.

    Args:
        title: 任务标题
        status: 任务状态
        priority: 任务优先级

    Returns:
        格式化的任务字符串（带图标）
    """
    status_icon = get_task_status_icon(status)
    return f"{status_icon} {title}"


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "SidebarContainer",
    "SidebarPane",
    "TasksPane",
    "GoalPane",
    "FileTreePane",
    "FilteredDirectoryTree",
    "AgentPane",
    "LogsPane",
    "SidebarTabBar",
    "get_log_level_icon",
    "format_log_entry",
    "get_task_status_icon",
    "format_task_item",
]