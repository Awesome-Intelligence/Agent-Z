#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugin Management CLI - 插件管理命令

参考 Hermes 插件 CLI 实现，提供：
- list: 列出已发现/已启用的插件
- info: 查看插件详细信息（manifest、状态、注册的 hooks/tools/providers）
- enable: 在配置中启用插件
- disable: 在配置中禁用插件
- validate: 校验插件 manifest / 加载路径
- reload: 强制重新扫描插件目录

🚪 Access - 💬 CLI - 插件管理
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common.logging_manager import get_system_logger

logger = get_system_logger("PluginCLI")


# ============================================================================
# Output helpers — minimal, no hard-coded UI texts for user-facing strings
# ============================================================================

def _get_ui():
    """Lazily grab the UI helpers so this module still imports cleanly without a terminal."""
    try:
        from common.terminal.colors import Colors, Theme
        from common.terminal.ui import print_header, print_substep, print_info, print_success, print_error, print_divider
        return (Colors, Theme, print_header, print_substep, print_info, print_success, print_error, print_divider)
    except Exception:
        return None


def _get_pm():
    from plugins import get_plugin_manager
    pm = get_plugin_manager()
    pm.discover_and_load()
    return pm


def _json_out(data: Any) -> None:
    print(_json.dumps(data, ensure_ascii=False, indent=2, default=str))


# ============================================================================
# list command
# ============================================================================

def list_plugins(
    *,
    include_disabled: bool = True,
    include_builtin: bool = True,
    json_output: bool = False,
    source_filter: Optional[str] = None,
) -> int:
    """List discovered plugins.

    Args:
        include_disabled: Show plugins that are disabled in config
        include_builtin: Show bundled/builtin plugins
        json_output: Emit machine-readable JSON instead of table
        source_filter: Only show plugins from one source (bundled|user|project|entrypoint)
    """
    try:
        pm = _get_pm()
    except Exception as e:
        if json_output:
            _json_out({"ok": False, "error": str(e)})
        else:
            print(f"Failed to load PluginManager: {e}")
        return 1

    manifests = pm.list_manifests(include_disabled=include_disabled, source=source_filter)

    rows: List[Dict[str, Any]] = []
    seen_names: set = set()
    pm_memory_providers = pm.get_memory_providers()
    for mf in manifests:
        if not include_builtin and mf.source == "bundled":
            continue
        name = mf.name or ""
        if not name:
            continue
        seen_names.add(name)
        loaded = name in pm.loaded_plugins
        is_disabled = pm.is_plugin_disabled(name)
        status = "loaded" if loaded else ("disabled" if is_disabled else "available")
        mem_provider_names = sorted(
            n for n in pm_memory_providers if n == name
        )
        rows.append({
            "name": name,
            "version": mf.version or "",
            "source": mf.source or "",
            "status": status,
            "enabled": not is_disabled,
            "loaded": loaded,
            "kind": mf.kind or "",
            "description": mf.description or "",
            "requires_env": list(mf.requires_env or []),
            "provides_tools": list(mf.provides_tools or []),
            "registers_providers": mem_provider_names,
            "hooks_count": len(mf.provides_hooks or []),
        })

    # Merge memory-providers discovered via plugins.memory subsystem (those have no plugin.yaml manifest at the root)
    try:
        from plugins.memory import discover_memory_providers
        memory_entries = discover_memory_providers()
    except Exception:
        memory_entries = []

    for mem_name, mem_available, mem_path in memory_entries:
        if mem_name in seen_names:
            continue
        if source_filter:
            continue
        if not include_builtin and str(mem_path).startswith("plugin://") is False and "bundled" in (source_filter or ""):
            pass
        source_label = (
            "user" if "user/plugins" in str(mem_path).replace("\\", "/") else "bundled"
        )
        if source_filter and source_label != source_filter:
            continue
        seen_names.add(mem_name)
        rows.append({
            "name": mem_name,
            "version": "",
            "source": source_label,
            "status": ("loaded" if mem_available else "available"),
            "enabled": True,
            "loaded": mem_available,
            "kind": "exclusive",
            "description": f"Memory provider plugin ({mem_name})",
            "requires_env": [],
            "provides_tools": [],
            "registers_providers": [mem_name],
            "hooks_count": 0,
        })

    rows.sort(key=lambda r: (r.get("source") or "", r.get("name") or ""))

    if json_output:
        _json_out({"ok": True, "plugins": rows})
        return 0

    ui = _get_ui()
    if ui is None:
        # Fallback plain output when terminal helpers unavailable
        for r in rows:
            print(f"[{r['source']:>10}] {r['name']:<20} v{r['version']:<8} {r['status']:<10} {r['description']}")
        if not rows:
            print("No plugins found.")
        return 0

    Colors, Theme, print_header, print_substep, print_info, print_success, print_error, print_divider = ui

    print_header("Plugins")
    print()

    if not rows:
        print_substep("  No plugins discovered.")
        print()
        return 0

    print_info(f"Discovered {len(rows)} plugin(s):")
    print()

    # Build a simple aligned table
    cols = [
        ("NAME", 20),
        ("VERSION", 10),
        ("SOURCE", 10),
        ("STATUS", 10),
        ("KIND", 9),
        ("TOOLS", 6),
        ("HOOKS", 6),
        ("DESCRIPTION", 40),
    ]
    header = "  ".join(f"{name:<{width}}" for name, width in cols)
    print_info(header)
    print_divider()

    for r in rows:
        status_color = Theme.SUCCESS if r["loaded"] else (Theme.WARNING if r["enabled"] else Theme.DIM)
        status = r["status"]
        name = r["name"]
        version = r["version"]
        source = r["source"]
        kind = r["kind"]
        n_tools = len(r["provides_tools"])
        n_hooks = r["hooks_count"]
        desc = (r["description"] or "")[:38]
        line = "  ".join([
            f"{name:<{cols[0][1]}}",
            f"{version:<{cols[1][1]}}",
            f"{source:<{cols[2][1]}}",
            f"{status_color}{status}{Colors.RESET}" + " " * max(0, cols[3][1] - len(status)),
            f"{kind:<{cols[4][1]}}",
            f"{n_tools:<{cols[5][1]}}",
            f"{n_hooks:<{cols[6][1]}}",
            f"{desc:<{cols[7][1]}}",
        ])
        print_substep(line)

    print()
    return 0


# ============================================================================
# info command
# ============================================================================

def _render_plugin_info(data: Dict[str, Any], *, json_output: bool) -> int:
    """Render the info view for a plugin given the assembled data dict."""
    if json_output:
        _json_out({"ok": True, "plugin": data})
        return 0

    ui = _get_ui()
    if ui is None:
        print(_json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return 0

    Colors, Theme, print_header, print_substep, print_info, print_success, print_error, print_divider = ui

    plugin_name = (data.get("manifest") or {}).get("name", "unknown")
    print_header(f"Plugin: {plugin_name}")
    print()

    m = data["manifest"]
    print_info("Manifest")
    print_substep(f"  Name         : {m['name']}")
    print_substep(f"  Version      : v{m['version']}" if m.get("version") else f"  Version      : (unknown)")
    print_substep(f"  Author       : {m['author'] or '(unknown)'}")
    print_substep(f"  Source       : {m['source'] or '(n/a)'}")
    print_substep(f"  Kind         : {m['kind'] or '(n/a)'}")
    print_substep(f"  Root         : {m['root'] or '(n/a)'}")
    print_substep(f"  Description  : {m['description'] or '(none)'}")
    print()

    env = m["requires_env"] or []
    print_info(f"Environment requirements ({len(env)})")
    if env:
        for name in env:
            if isinstance(name, dict):
                key = name.get("name") or name.get("key") or str(name)
                print_substep(f"  - {key}")
            else:
                print_substep(f"  - {name}")
    else:
        print_substep("  (none)")
    print()

    tools = m["provides_tools"] or []
    print_info(f"Provides tools ({len(tools)})")
    if tools:
        for t in tools:
            print_substep(f"  - {t}")
    else:
        print_substep("  (none declared in manifest)")
    print()

    hooks = m["provides_hooks"] or []
    print_info(f"Declares hooks ({len(hooks)})")
    if hooks:
        for h in hooks:
            print_substep(f"  - {h}")
    else:
        print_substep("  (none)")
    print()

    print_info("Status")
    enabled = data.get("enabled", False)
    loaded = data.get("loaded") or {}
    if loaded.get("loaded"):
        print_substep(f"  Enabled : {Theme.SUCCESS + 'yes' + Colors.RESET if enabled else Theme.WARNING + 'no' + Colors.RESET}")
        print_substep(f"  Loaded  : {Theme.SUCCESS + 'yes' + Colors.RESET}")
        print_substep(f"  Module  : {loaded.get('module') or '(unknown)'}")
        print_substep(f"  Hooks registered   : {loaded.get('hooks_registered', 0)}")
        print_substep(f"  Tools registered   : {loaded.get('tools_registered', 0)}")
        print_substep(f"  Providers registered: {loaded.get('providers_registered', 0)}")
    else:
        print_substep(f"  Enabled : {Theme.SUCCESS + 'yes' + Colors.RESET if enabled else Theme.WARNING + 'no' + Colors.RESET}")
        print_substep(f"  Loaded  : {Theme.WARNING + 'no' + Colors.RESET}")
        err = loaded.get("load_error") or loaded.get("error")
        if err:
            print_error(f"  Load error: {err}")
    print()

    counts = data.get("provider_registry_counts") or {}
    if counts:
        print_info("Provider registries")
        for k, v in counts.items():
            print_substep(f"  - {k}: {v}")
        print()

    return 0


def plugin_info(plugin_name: str, *, json_output: bool = False) -> int:
    try:
        pm = _get_pm()
    except Exception as e:
        if json_output:
            _json_out({"ok": False, "error": str(e)})
        else:
            print(f"Failed to load PluginManager: {e}")
        return 1

    mf = pm.get_manifest(plugin_name)
    if mf is None:
        # Fallback: check if it's a memory-plugin discovered via plugins.memory subsystem
        try:
            from plugins.memory import load_memory_provider, diagnose_provider
            mem_provider = load_memory_provider(plugin_name)
        except Exception:
            mem_provider = None
            diagnose_provider = None  # type: ignore

        if mem_provider is None:
            msg = f"Plugin '{plugin_name}' not found"
            if json_output:
                _json_out({"ok": False, "error": msg})
            else:
                print(msg)
            return 2

        # Build a pseudo-manifest view for this memory plugin
        try:
            diag = diagnose_provider(plugin_name) if diagnose_provider else None
        except Exception:
            diag = None
        diag_path = getattr(diag, "path", None) if diag else None
        try:
            source_label = (
                "user" if diag_path and "user/plugins" in str(diag_path).replace("\\", "/") else "bundled"
            )
        except Exception:
            source_label = "bundled"
        data = {
            "manifest": {
                "name": plugin_name,
                "version": "",
                "description": f"Memory provider plugin ({plugin_name})",
                "author": "",
                "kind": "exclusive",
                "source": source_label,
                "root": diag_path or "",
                "requires_env": [],
                "provides_tools": getattr(diag, "available_tools", None) or [],
                "provides_hooks": [],
            },
            "enabled": True,
            "loaded": {
                "loaded": True,
                "module": type(mem_provider).__module__,
                "hooks_registered": 0,
                "tools_registered": len(diag.available_tools) if diag else 0,
                "providers_registered": 1,
                "error": diag.error if diag else None,
            },
            "provider_registry_counts": {
                "memory_providers": 1,
            },
        }
        if json_output:
            _json_out({"ok": True, "plugin": data})
            return 0
        return _render_plugin_info(data, json_output=json_output)

    loaded_info: Dict[str, Any] = {}
    if plugin_name in pm.loaded_plugins:
        entry = pm.loaded_plugins[plugin_name]
        loaded_info = {
            "loaded": True,
            "module": entry.module.__name__ if entry.module else None,
            "hooks_registered": entry.hooks_registered,
            "tools_registered": entry.tools_registered,
            "providers_registered": entry.providers_registered,
            "error": entry.error,
        }
    else:
        loaded_info = {
            "loaded": False,
            "load_error": pm.load_errors.get(plugin_name),
        }

    # Merge provider type counts from PluginManager registries (use public getters)
    provider_counts: Dict[str, int] = {}
    registry_map = {
        "memory_providers": pm.get_memory_providers(),
        "context_engines": pm.get_context_engines(),
        "model_providers": pm.get_model_providers(),
        "web_search_backends": pm.get_web_search_backends(),
        "tool_providers": pm.get_tool_providers(),
    }
    for key, registry in registry_map.items():
        if registry:
            provider_counts[key] = len(registry)

    data = {
        "manifest": {
            "name": mf.name,
            "version": mf.version,
            "description": mf.description,
            "author": mf.author,
            "kind": mf.kind,
            "source": mf.source,
            "root": str(mf.path) if mf.path else None,
            "requires_env": list(mf.requires_env or []),
            "provides_tools": list(mf.provides_tools or []),
            "provides_hooks": list(mf.provides_hooks or []),
        },
        "enabled": not pm.is_plugin_disabled(plugin_name),
        "loaded": loaded_info,
        "provider_registry_counts": provider_counts,
    }

    if json_output:
        _json_out({"ok": True, "plugin": data})
        return 0

    return _render_plugin_info(data, json_output=json_output)


# ============================================================================
# enable / disable commands
# ============================================================================

def _read_plugin_config_file() -> Optional[Path]:
    try:
        from common.config import AGENT_Z_HOME
        cfg_file = AGENT_Z_HOME / "plugins" / "plugins.yaml"
        return cfg_file
    except Exception:
        return None


def _load_plugins_config() -> Dict[str, Any]:
    cfg_file = _read_plugin_config_file()
    if cfg_file is None or not cfg_file.exists():
        return {"enabled": {}, "disabled": []}

    try:
        try:
            import yaml  # type: ignore
            with cfg_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except ImportError:
            # Fallback: plain JSON-ish YAML subset parser
            try:
                import json
                text = cfg_file.read_text(encoding="utf-8")
                data = json.loads(text)
            except Exception:
                data = {}
    except Exception as e:
        logger.warning(f"Failed to read plugins config {cfg_file}: {e}")
        data = {}

    if not isinstance(data, dict):
        data = {}
    data.setdefault("enabled", {})
    data.setdefault("disabled", [])
    return data


def _save_plugins_config(cfg: Dict[str, Any]) -> Optional[Path]:
    cfg_file = _read_plugin_config_file()
    if cfg_file is None:
        return None

    try:
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            import yaml  # type: ignore
            text = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        except ImportError:
            import json
            text = json.dumps(cfg, ensure_ascii=False, indent=2)
        cfg_file.write_text(text, encoding="utf-8")
        return cfg_file
    except Exception as e:
        logger.warning(f"Failed to save plugins config {cfg_file}: {e}")
        return None


def enable_plugin(plugin_name: str, *, json_output: bool = False) -> int:
    try:
        pm = _get_pm()
    except Exception as e:
        if json_output:
            _json_out({"ok": False, "error": str(e)})
        else:
            print(f"Failed to load PluginManager: {e}")
        return 1

    mf = pm.get_manifest(plugin_name)
    if mf is None:
        msg = f"Plugin '{plugin_name}' not found"
        if json_output:
            _json_out({"ok": False, "error": msg})
        else:
            print(msg)
        return 2

    cfg = _load_plugins_config()
    if "disabled" in cfg and isinstance(cfg["disabled"], list) and plugin_name in cfg["disabled"]:
        cfg["disabled"].remove(plugin_name)

    cfg["enabled"] = cfg.get("enabled") or {}
    if not isinstance(cfg["enabled"], dict):
        cfg["enabled"] = {}
    cfg["enabled"][plugin_name] = True

    saved = _save_plugins_config(cfg)

    ui = _get_ui()
    if json_output:
        _json_out({
            "ok": True,
            "plugin": plugin_name,
            "action": "enabled",
            "config_path": str(saved) if saved else None,
        })
        return 0

    if ui:
        _, _, _, print_substep, _, print_success, _, _ = ui
        print_success(f"Plugin '{plugin_name}' enabled")
        if saved:
            print_substep(f"  Config saved: {saved}")
    else:
        print(f"Enabled plugin '{plugin_name}'")

    return 0


def disable_plugin(plugin_name: str, *, json_output: bool = False) -> int:
    try:
        pm = _get_pm()
    except Exception as e:
        if json_output:
            _json_out({"ok": False, "error": str(e)})
        else:
            print(f"Failed to load PluginManager: {e}")
        return 1

    # We allow disabling even a plugin we haven't discovered (user may want this pre-emptively)
    cfg = _load_plugins_config()

    if "disabled" not in cfg or not isinstance(cfg["disabled"], list):
        cfg["disabled"] = []
    if plugin_name not in cfg["disabled"]:
        cfg["disabled"].append(plugin_name)

    if "enabled" in cfg and isinstance(cfg["enabled"], dict) and plugin_name in cfg["enabled"]:
        del cfg["enabled"][plugin_name]

    saved = _save_plugins_config(cfg)

    ui = _get_ui()
    if json_output:
        _json_out({
            "ok": True,
            "plugin": plugin_name,
            "action": "disabled",
            "config_path": str(saved) if saved else None,
        })
        return 0

    if ui:
        _, _, _, print_substep, _, print_success, _, _ = ui
        print_success(f"Plugin '{plugin_name}' disabled")
        if saved:
            print_substep(f"  Config saved: {saved}")
    else:
        print(f"Disabled plugin '{plugin_name}'")

    return 0


# ============================================================================
# validate command
# ============================================================================

@dataclass
class ValidationIssue:
    level: str  # "error" | "warning" | "info"
    code: str
    message: str


def validate_plugin(plugin_name: str, *, json_output: bool = False) -> int:
    issues: List[ValidationIssue] = []
    manifest_info: Dict[str, Any] = {}

    try:
        pm = _get_pm()
    except Exception as e:
        issues.append(ValidationIssue("error", "manager_unreachable", str(e)))
        if json_output:
            _json_out({"ok": False, "valid": False, "issues": [i.__dict__ for i in issues]})
        else:
            print(f"PluginManager failed: {e}")
        return 1

    mf = pm.get_manifest(plugin_name)

    # Fallback: if plugin manifest is not in PM, maybe it's a memory-plugin loaded via plugins.memory
    if mf is None:
        try:
            from plugins.memory import load_memory_provider, diagnose_provider
            mem_provider = load_memory_provider(plugin_name)
        except Exception:
            mem_provider = None
            diagnose_provider = None  # type: ignore

        if mem_provider is None:
            issues.append(ValidationIssue("error", "manifest_not_found",
                                           f"Plugin '{plugin_name}' manifest not found"))
            if json_output:
                _json_out({"ok": True, "valid": False, "issues": [i.__dict__ for i in issues]})
            else:
                print(f"Plugin '{plugin_name}' not found")
            return 2

        # Validate memory-plugin by its diagnostics
        try:
            diag = diagnose_provider(plugin_name, force_refresh=True) if diagnose_provider else None
        except Exception as e:
            diag = None
            issues.append(ValidationIssue("warning", "diagnose_failed", str(e)))

        diag_path = getattr(diag, "path", None) if diag else None
        manifest_info = {
            "name": plugin_name,
            "version": "",
            "source": (
                "user" if diag_path and "user/plugins" in str(diag_path).replace("\\", "/") else "bundled"
            ),
            "root": diag_path or "",
            "category": "memory_provider",
        }

        # Memory provider availability check
        try:
            available = mem_provider.is_available()
        except Exception as e:
            available = False
            issues.append(ValidationIssue("error", "availability_check_failed", str(e)))

        if not available:
            issues.append(ValidationIssue("warning", "provider_unavailable",
                                           "Provider reports is_available() = False"))

        # Config schema / required methods
        required_methods = ["is_available", "initialize", "get_tool_schemas", "system_prompt_block"]
        for m in required_methods:
            if not callable(getattr(mem_provider, m, None)):
                issues.append(ValidationIssue("warning", "missing_method",
                                               f"Memory provider missing required method: {m}"))

        try:
            schema = mem_provider.get_config_schema()
            if not isinstance(schema, list):
                issues.append(ValidationIssue("warning", "bad_config_schema",
                                               "get_config_schema() did not return a list"))
        except Exception as e:
            issues.append(ValidationIssue("warning", "config_schema_failed", str(e)))

        valid = not any(i.level == "error" for i in issues)
        return _render_validation_result(plugin_name, manifest_info, issues, valid, json_output=json_output)

    manifest_info = {
        "name": mf.name,
        "version": mf.version,
        "source": mf.source,
        "root": str(mf.path) if mf.path else None,
    }

    if mf.name and plugin_name != mf.name:
        issues.append(ValidationIssue("warning", "name_mismatch",
                                       f"Directory/plugin name '{plugin_name}' does not match manifest name '{mf.name}'"))

    if not mf.version:
        issues.append(ValidationIssue("error", "missing_version", "Manifest is missing version"))

    if not mf.description:
        issues.append(ValidationIssue("warning", "missing_description",
                                       "Manifest is missing description (will appear blank in listings)"))

    if mf.kind not in ("shared", "exclusive", "backend", "platform", "model-provider", "standalone"):
        issues.append(ValidationIssue("warning", "unknown_kind",
                                       f"Manifest kind '{mf.kind}' is not standard"))

    # Ensure required_env can actually be resolved (best effort)
    import os
    for env_name in (mf.requires_env or []):
        env_key = env_name
        if isinstance(env_name, dict):
            env_key = env_name.get("name") or env_name.get("key") or str(env_name)
        if not os.environ.get(env_key):
            issues.append(ValidationIssue("warning", "env_missing",
                                           f"Required env '{env_key}' is not set (plugin will still load but may be non-functional)"))

    # Try to load
    pm.discover_and_load(force=True, only=[plugin_name])
    if plugin_name not in pm.loaded_plugins:
        err = pm.load_errors.get(plugin_name)
        issues.append(ValidationIssue("error", "load_failed",
                                       f"Plugin failed to load: {err}"))
    else:
        load_entry = pm.loaded_plugins[plugin_name]
        if load_entry.error:
            issues.append(ValidationIssue("error", "load_partial",
                                           f"Plugin loaded with error: {load_entry.error}"))

    valid = not any(i.level == "error" for i in issues)
    return _render_validation_result(plugin_name, manifest_info, issues, valid, json_output=json_output)


def _render_validation_result(
    plugin_name: str,
    manifest_info: Dict[str, Any],
    issues: List[ValidationIssue],
    valid: bool,
    *,
    json_output: bool,
) -> int:
    if json_output:
        _json_out({
            "ok": True,
            "valid": valid,
            "manifest": manifest_info,
            "issues": [i.__dict__ for i in issues],
        })
        return 0 if valid else 3

    ui = _get_ui()
    if ui:
        Colors, Theme, print_header, print_substep, print_info, print_success, print_error, print_divider = ui
    else:
        Colors = Theme = None
        def noop(*a, **k): pass
        print_header = print_substep = print_info = print_success = print_error = print_divider = noop

    print_header(f"Validate plugin: {plugin_name}")
    print()
    print_info("Manifest")
    for k, v in manifest_info.items():
        print_substep(f"  {k:<12}: {v}")
    print()

    if not issues:
        print_success("No issues found. Plugin is valid.")
        print()
        return 0

    print_info(f"Issues ({len(issues)})")
    for issue in issues:
        tag = (Theme.ERROR if issue.level == "error" else
               (Theme.WARNING if issue.level == "warning" else Theme.DIM))
        label = issue.level.upper()
        prefix = f"  {tag}[{label}]{Colors.RESET}"
        print_substep(f"{prefix} ({issue.code}) {issue.message}")
    print()

    return 0 if valid else 3


# ============================================================================
# reload command
# ============================================================================

def reload_plugins(*, json_output: bool = False) -> int:
    try:
        from plugins import get_plugin_manager
        pm = get_plugin_manager()
        loaded = pm.discover_and_load(force=True)
    except Exception as e:
        if json_output:
            _json_out({"ok": False, "error": str(e)})
        else:
            print(f"Failed to reload plugins: {e}")
        return 1

    if json_output:
        _json_out({
            "ok": True,
            "reloaded": True,
            "discovered": [m.name for m in pm.list_manifests()],
            "loaded": list(pm.loaded_plugins.keys()),
            "load_errors": list(pm.load_errors.keys()),
        })
        return 0

    ui = _get_ui()
    if ui:
        _, _, _, print_substep, _, print_success, _, _ = ui
    else:
        def noop(*a, **k): pass
        print_substep = print_success = noop

    print_success("Plugins reloaded")
    print_substep(f"  Discovered: {len(list(pm.list_manifests()))}")
    print_substep(f"  Loaded    : {len(pm.loaded_plugins)}")
    if pm.load_errors:
        for name, err in pm.load_errors.items():
            print_substep(f"  Errors for {name}: {err}")
    print()
    return 0


# ============================================================================
# Provider registry listing
# ============================================================================

def list_providers(*, json_output: bool = False) -> int:
    try:
        pm = _get_pm()
    except Exception as e:
        if json_output:
            _json_out({"ok": False, "error": str(e)})
        else:
            print(f"Failed to load PluginManager: {e}")
        return 1

    memory_from_pm = list(pm.get_memory_providers().keys())
    try:
        from plugins.memory import discover_memory_providers
        memory_from_discovery = [name for name, _avail, _p in discover_memory_providers()]
    except Exception:
        memory_from_discovery = []

    memory_providers = sorted(set(memory_from_pm) | set(memory_from_discovery))

    out: Dict[str, Any] = {
        "memory_providers": memory_providers,
        "context_engines": list(pm.get_context_engines().keys()),
        "model_providers": list(pm.get_model_providers().keys()),
        "web_search_backends": list(pm.get_web_search_backends().keys()),
        "tool_providers": list(pm.get_tool_providers().keys()),
        "plugins": list(pm.loaded_plugins.keys()),
    }

    if json_output:
        _json_out({"ok": True, "registries": out})
        return 0

    ui = _get_ui()
    if ui:
        _, _, print_header, print_substep, print_info, _, _, _ = ui
    else:
        def noop(*a, **k): pass
        print_header = print_substep = print_info = noop

    print_header("Plugin registrations")
    print()
    for key, names in out.items():
        print_info(f"{key.replace('_', ' ').title()} ({len(names)})")
        if names:
            for n in names:
                print_substep(f"  - {n}")
        else:
            print_substep("  (none)")
        print()
    return 0


# ============================================================================
# Public high-level dispatcher used by main.py cmd_plugins
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Accepts a list of CLI args (no program name).

    Supported::

        list [--json] [--enabled-only] [--source SOURCE]
        info <name> [--json]
        enable <name> [--json]
        disable <name> [--json]
        validate <name> [--json]
        reload [--json]
        providers [--json]
    """
    import argparse

    parser = argparse.ArgumentParser(prog="plugins", description="Plugin management")
    sub = parser.add_subparsers(dest="cmd", metavar="CMD")

    p_list = sub.add_parser("list", help="List discovered plugins")
    p_list.add_argument("--json", action="store_true", dest="json_output")
    p_list.add_argument("--enabled-only", action="store_true", dest="enabled_only")
    p_list.add_argument("--no-builtin", action="store_true", dest="no_builtin")
    p_list.add_argument("--source", choices=["bundled", "user", "project", "entrypoint"], default=None)

    p_info = sub.add_parser("info", help="Show plugin details")
    p_info.add_argument("name")
    p_info.add_argument("--json", action="store_true", dest="json_output")

    p_enable = sub.add_parser("enable", help="Enable a plugin in user config")
    p_enable.add_argument("name")
    p_enable.add_argument("--json", action="store_true", dest="json_output")

    p_disable = sub.add_parser("disable", help="Disable a plugin in user config")
    p_disable.add_argument("name")
    p_disable.add_argument("--json", action="store_true", dest="json_output")

    p_validate = sub.add_parser("validate", help="Validate a plugin manifest & load")
    p_validate.add_argument("name")
    p_validate.add_argument("--json", action="store_true", dest="json_output")

    p_reload = sub.add_parser("reload", help="Force re-scan / re-load of all plugins")
    p_reload.add_argument("--json", action="store_true", dest="json_output")

    p_providers = sub.add_parser("providers", help="List things registered by plugins (memory/context/model providers...)")
    p_providers.add_argument("--json", action="store_true", dest="json_output")

    args = parser.parse_args(argv or (["list"] if argv is None else argv))

    if args.cmd is None or args.cmd == "list":
        return list_plugins(
            include_disabled=not getattr(args, "enabled_only", False),
            include_builtin=not getattr(args, "no_builtin", False),
            json_output=getattr(args, "json_output", False),
            source_filter=getattr(args, "source", None),
        )
    if args.cmd == "info":
        return plugin_info(args.name, json_output=args.json_output)
    if args.cmd == "enable":
        return enable_plugin(args.name, json_output=args.json_output)
    if args.cmd == "disable":
        return disable_plugin(args.name, json_output=args.json_output)
    if args.cmd == "validate":
        return validate_plugin(args.name, json_output=args.json_output)
    if args.cmd == "reload":
        return reload_plugins(json_output=args.json_output)
    if args.cmd == "providers":
        return list_providers(json_output=args.json_output)

    parser.print_help()
    return 2


__all__ = [
    "list_plugins",
    "plugin_info",
    "enable_plugin",
    "disable_plugin",
    "validate_plugin",
    "reload_plugins",
    "list_providers",
    "main",
]
