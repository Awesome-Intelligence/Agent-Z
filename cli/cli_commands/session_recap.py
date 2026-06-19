#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Recap command - Generate session summary

🚪 Access - 💬 CLI - 会话摘要

提供会话摘要生成功能，支持 Markdown 格式输出。
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


def generate_session_recap(session_id: Optional[str] = None, format: str = "markdown") -> None:
    """Generate session recap.
    
    Args:
        session_id: Session ID to recap (default: current/last)
        format: Output format (markdown/text/json)
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_error, print_info
    
    print_header("📝 会话摘要")
    
    # 获取会话
    if not session_id:
        session_id = _get_last_session_id()
    
    if not session_id:
        print_error("没有可用的会话")
        return
    
    # 获取会话数据
    session_data = _get_session_data(session_id)
    
    if not session_data:
        print_error(f"会话不存在: {session_id}")
        return
    
    # 生成摘要
    recap = _create_recap(session_data)
    
    # 输出
    if format == "json":
        import json
        print(json.dumps(recap, indent=2, ensure_ascii=False))
    elif format == "markdown":
        _print_markdown_recap(recap)
    else:
        _print_text_recap(recap)


def _get_last_session_id() -> Optional[str]:
    """获取最近会话 ID"""
    try:
        from agent.session import session_manager
        sessions = session_manager.list_sessions()
        return sessions[-1] if sessions else None
    except Exception:
        return None


def _get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    """获取会话数据"""
    try:
        from agent.session import session_manager
        session = session_manager.get_session(session_id)
        if not session:
            return None
        
        return {
            "id": session_id,
            "created_at": getattr(session, 'created_at', None),
            "updated_at": getattr(session, 'updated_at', None),
            "messages": getattr(session, 'messages', []),
            "metadata": getattr(session, 'metadata', {}),
        }
    except Exception:
        return None


def _create_recap(session_data: Dict) -> Dict:
    """创建会话摘要"""
    messages = session_data.get("messages", [])
    
    # 统计信息
    user_messages = [m for m in messages if m.get("role") == "user"]
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    tool_messages = [m for m in messages if m.get("role") == "tool"]
    
    # 提取主题
    topics = _extract_topics(messages)
    
    # 提取工具使用
    tools_used = _extract_tools_used(messages)
    
    # 计算 token 估算
    total_tokens = _estimate_tokens(messages)
    
    created_at = session_data.get("created_at")
    if created_at:
        duration = datetime.now() - created_at
        duration_str = _format_duration(duration)
    else:
        duration_str = "Unknown"
    
    return {
        "session_id": session_data.get("id", "unknown"),
        "created_at": created_at.strftime("%Y-%m-%d %H:%M") if created_at else "Unknown",
        "duration": duration_str,
        "stats": {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "tool_calls": len(tool_messages),
            "estimated_tokens": total_tokens,
        },
        "topics": topics,
        "tools_used": tools_used,
        "first_message": user_messages[0].get("content", "")[:100] if user_messages else "",
        "last_message": (assistant_messages[-1].get("content", "") if assistant_messages else "")[:200],
    }


def _extract_topics(messages: List[Dict]) -> List[str]:
    """提取会话主题"""
    topics = []
    
    # 简单的主题提取
    keywords = {
        "代码": ["代码", "函数", "类", "实现", "debug", "bug"],
        "文件": ["文件", "读取", "写入", "编辑", "path"],
        "Git": ["git", "commit", "branch", "merge"],
        "终端": ["命令", "terminal", "bash", "shell"],
        "测试": ["test", "测试", "单元测试", "pytest"],
        "文档": ["文档", "readme", "comment", "docstring"],
    }
    
    all_content = " ".join([
        m.get("content", "") 
        for m in messages 
        if isinstance(m.get("content"), str)
    ]).lower()
    
    for topic, words in keywords.items():
        if any(w.lower() in all_content for w in words):
            topics.append(topic)
    
    return topics[:5]  # 最多5个主题


def _extract_tools_used(messages: List[Dict]) -> List[str]:
    """提取使用的工具"""
    tools = set()
    
    for m in messages:
        if m.get("role") == "tool":
            tool_name = m.get("name", "")
            if tool_name:
                tools.add(tool_name)
    
    return sorted(list(tools))


def _estimate_tokens(messages: List[Dict]) -> int:
    """估算 token 数量"""
    total_chars = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
    
    # 简单估算: 1 token ≈ 4 字符
    return total_chars // 4


def _format_duration(duration) -> str:
    """格式化时长"""
    seconds = duration.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def _print_markdown_recap(recap: Dict) -> None:
    """打印 Markdown 格式摘要"""
    from common.terminal.colors import Colors, color
    
    print()
    print(f"# 📝 会话摘要")
    print()
    print(f"**会话 ID**: `{recap['session_id'][:16]}...`")
    print(f"**创建时间**: {recap['created_at']}")
    print(f"**持续时间**: {recap['duration']}")
    print()
    
    print("## 📊 统计")
    print()
    print(f"- 总消息数: {recap['stats']['total_messages']}")
    print(f"- 用户消息: {recap['stats']['user_messages']}")
    print(f"- 助手回复: {recap['stats']['assistant_messages']}")
    print(f"- 工具调用: {recap['stats']['tool_calls']}")
    print(f"- 估算 Token: {recap['stats']['estimated_tokens']:,}")
    print()
    
    if recap['topics']:
        print("## 🏷️ 主题")
        print()
        print(", ".join(recap['topics']))
        print()
    
    if recap['tools_used']:
        print("## 🔧 使用的工具")
        print()
        for tool in recap['tools_used']:
            print(f"- `{tool}`")
        print()
    
    if recap['first_message']:
        print("## 💬 开始")
        print()
        print(f"> {recap['first_message'][:200]}...")
        print()
    
    if recap['last_message']:
        print("## 🔚 最后回复")
        print()
        print(f"> {recap['last_message'][:200]}...")
        print()


def _print_text_recap(recap: Dict) -> None:
    """打印纯文本格式摘要"""
    from common.terminal.colors import Colors, color
    
    print()
    print(color("会话摘要", Colors.AVOCADO_BRIGHT))
    print(color("=" * 50, Colors.AVOCADO_DIM))
    print()
    print(f"会话 ID: {recap['session_id'][:16]}...")
    print(f"创建时间: {recap['created_at']}")
    print(f"持续时间: {recap['duration']}")
    print()
    print(f"总消息数: {recap['stats']['total_messages']}")
    print(f"工具调用: {recap['stats']['tool_calls']}")
    print(f"估算 Token: {recap['stats']['estimated_tokens']:,}")
    print()
    
    if recap['topics']:
        print(f"主题: {', '.join(recap['topics'])}")
    
    if recap['tools_used']:
        print(f"工具: {', '.join(recap['tools_used'])}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate session recap")
    parser.add_argument("session_id", nargs="?", help="Session ID")
    parser.add_argument("-f", "--format", choices=["markdown", "text", "json"],
                        default="markdown", help="Output format")
    
    args = parser.parse_args()
    
    generate_session_recap(session_id=args.session_id, format=args.format)