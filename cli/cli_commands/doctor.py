#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Doctor command - System diagnostic checks

🚪 Access - 💬 CLI - 诊断检查

运行系统诊断检查，验证配置和依赖。
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any


def run_diagnostics(verbose: bool = False) -> bool:
    """Run diagnostic checks on system configuration.
    
    Args:
        verbose: Show detailed output
        
    Returns:
        True if all checks pass, False otherwise
    """
    from cli.components.colors import Colors, color
    from cli.components.ui import print_header, print_info, print_success, print_error
    
    print_header("🔍 系统诊断")
    print()
    
    checks = [
        ("Python 版本", check_python_version),
        ("依赖包", check_dependencies),
        ("LLM 配置", check_llm_config),
        ("工具注册", check_tools),
        ("会话目录", check_session_dir),
        ("日志目录", check_log_dir),
        ("网络连接", check_network),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_func in checks:
        try:
            result = check_func()
            if result["status"] == "ok":
                print_success(f"{name}: {result['message']}")
                passed += 1
            elif result["status"] == "warning":
                print_info(f"{name}: {result['message']}")
            else:
                print_error(f"{name}: {result['message']}")
                failed += 1
        except Exception as e:
            print_error(f"{name}: {e}")
            failed += 1
        
        if verbose:
            print()
    
    print()
    print_info(f"结果: {passed} 通过, {failed} 失败")
    
    return failed == 0


def check_python_version() -> Dict[str, Any]:
    """Check Python version."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        return {"status": "ok", "message": f"Python {version.major}.{version.minor}.{version.micro}"}
    else:
        return {"status": "warning", "message": f"Python {version.major}.{version.minor} (建议 >= 3.10)"}


def check_dependencies() -> Dict[str, Any]:
    """Check required dependencies."""
    required = ["rich", "yaml", "prompt_toolkit"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    
    if not missing:
        return {"status": "ok", "message": "所有依赖已安装"}
    else:
        return {"status": "warning", "message": f"缺少可选依赖: {', '.join(missing)}"}


def check_llm_config() -> Dict[str, Any]:
    """Check LLM configuration."""
    try:
        from common.config import load_config
        config = load_config()
        
        provider = config.get("llm", {}).get("provider")
        model = config.get("model", {}).get("name")
        
        if provider and model:
            return {"status": "ok", "message": f"{provider}/{model}"}
        else:
            return {"status": "warning", "message": "LLM 未配置 (运行 setup)"}
    except Exception:
        return {"status": "warning", "message": "无法读取配置"}


def check_tools() -> Dict[str, Any]:
    """Check tool registration."""
    try:
        from tools.registry import tool_registry
        count = len(tool_registry.list_tools())
        if count > 0:
            return {"status": "ok", "message": f"{count} 个工具已注册"}
        else:
            return {"status": "warning", "message": "无工具已注册"}
    except Exception:
        return {"status": "warning", "message": "无法检查工具"}


def check_session_dir() -> Dict[str, Any]:
    """Check session directory."""
    from agent.workspace import get_workspace_manager
    
    try:
        wm = get_workspace_manager()
        session_dir = wm.workspace_dir / "sessions"
        
        if session_dir.exists():
            return {"status": "ok", "message": str(session_dir)}
        else:
            return {"status": "warning", "message": "会话目录不存在"}
    except Exception:
        return {"status": "warning", "message": "无法检查会话目录"}


def check_log_dir() -> Dict[str, Any]:
    """Check log directory."""
    from common.config import get_logs_dir
    
    try:
        log_dir = get_logs_dir()
        
        if log_dir.exists():
            return {"status": "ok", "message": str(log_dir)}
        else:
            return {"status": "warning", "message": "日志目录不存在"}
    except Exception:
        return {"status": "warning", "message": "无法检查日志目录"}


def check_network() -> Dict[str, Any]:
    """Check network connectivity."""
    import urllib.request
    
    try:
        urllib.request.urlopen("https://api.openai.com", timeout=3)
        return {"status": "ok", "message": "网络连接正常"}
    except Exception:
        return {"status": "warning", "message": "无法连接到外网"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run system diagnostics")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    success = run_diagnostics(verbose=args.verbose)
    sys.exit(0 if success else 1)