#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI Widgets - Textual UI Widget Components

🚪 Access - 💬 CLI - TUI Widgets

提供 Textual TUI 所需的组件库，包括：
- ChatItem: 单条消息 widget（oterm 风格 reactive + MarkdownStream）
- ChatContainer: 消息列表容器（oterm 风格 VerticalScroll）
- ApprovalDialog: 权限审批对话框

历史组件（已删除，迁移到 oterm 风格）：
- MessageList（被 ChatContainer 替代）
- StreamingText（被 ChatItem.append_text + MarkdownStream 替代）
"""

# 单条消息 widget
try:
    from .chat_item import (
        ChatItem,
        ToolCallItem,
    )
except ImportError:
    ChatItem = None
    ToolCallItem = None

# 消息列表容器
try:
    from .chat_container import ChatContainer
except ImportError:
    ChatContainer = None

# 审批对话框组件
try:
    from .approval_dialog import (
        ApprovalDialog,
        ApprovalMode,
        RiskLevel,
        SENSITIVE_OPERATIONS,
        ApprovalManager,
        ApprovalRequested,
        ApprovalConfirmed,
        ApprovalRejected,
        create_approval_dialog,
    )
except ImportError:
    ApprovalDialog = None
    ApprovalMode = None
    RiskLevel = None
    SENSITIVE_OPERATIONS = None
    ApprovalManager = None
    ApprovalRequested = None
    ApprovalConfirmed = None
    ApprovalRejected = None
    create_approval_dialog = None

# 输入队列悬浮面板
try:
    from .input_queue_panel import InputQueuePanel
except ImportError:
    InputQueuePanel = None

__all__ = [
    # 消息组件（oterm 风格）
    "ChatItem",
    "ChatContainer",
    "ToolCallItem",
    # 审批对话框
    "ApprovalDialog",
    "ApprovalMode",
    "RiskLevel",
    "SENSITIVE_OPERATIONS",
    "ApprovalManager",
    "ApprovalRequested",
    "ApprovalConfirmed",
    "ApprovalRejected",
    "create_approval_dialog",
    # 输入队列悬浮面板
    "InputQueuePanel",
]
