#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Provider Plugin System - 外部记忆 Provider 插件

参考 Hermes Agent 的插件架构设计，接入 Agent-Z PluginManager：
- 插件发现 (discover_memory_providers) — 优先使用 PluginManager 注册结果
- 动态加载 (load_memory_provider) — 保持旧的直接加载路径作为备用
- 配置校验 (validate_provider_config)
- 错误处理和诊断 (ProviderDiagnostics)

标准插件需要导出：
    def register(ctx: "PluginContext") -> None:
        ctx.register_memory_provider(<MemoryProviderInstance>())

Usage:
    from plugins.memory import discover_memory_providers, load_memory_provider

    providers = discover_memory_providers()
    provider = load_memory_provider("example")
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

from common.config import AGENT_Z_HOME
from common.logging_manager import get_system_logger

if TYPE_CHECKING:
    from agent.memory.memory_provider import MemoryProvider

logger = get_system_logger("MemoryPlugin")

_PLUGINS_DIR = Path(__file__).parent
_USER_PLUGINS_DIR = AGENT_Z_HOME / "plugins" / "memory"

_discovered: Optional[List[Tuple[str, Path]]] = None
_loaded_providers: Dict[str, "MemoryProvider"] = {}
_diagnostics_cache: Dict[str, "ProviderDiagnostics"] = {}


# ============================================================================
# Provider Status & Diagnostics
# ============================================================================

class ProviderStatus(str, Enum):
    NOT_FOUND = "not_found"
    FOUND_BUT_UNAVAILABLE = "found_but_unavailable"
    AVAILABLE = "available"
    LOADED = "loaded"
    ERROR = "error"
    CONFIG_INVALID = "config_invalid"


@dataclass
class ProviderDiagnostics:
    name: str
    status: ProviderStatus
    path: Optional[str] = None
    is_available: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    config_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    config_schema: List[Dict[str, Any]] = field(default_factory=list)
    last_check: Optional[float] = None

    @property
    def is_valid(self) -> bool:
        return self.status in (ProviderStatus.AVAILABLE, ProviderStatus.LOADED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "path": self.path,
            "is_available": self.is_available,
            "is_valid": self.is_valid,
            "error": self.error,
            "error_type": self.error_type,
            "config_errors": self.config_errors,
            "warnings": self.warnings,
            "available_tools": self.available_tools,
            "config_schema": self.config_schema,
        }


@dataclass
class ProviderValidationResult:
    provider_name: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


# ============================================================================
# Plugin Context (memory provider specific, for direct loading path)
# ============================================================================

class _LegacyPluginContext:
    def __init__(self, name: str):
        self._name = name
        self._provider: Optional["MemoryProvider"] = None

    @property
    def name(self) -> str:
        return self._name

    def register_memory_provider(self, provider: "MemoryProvider") -> None:
        self._provider = provider

    @property
    def provider(self) -> Optional["MemoryProvider"]:
        return self._provider


# ============================================================================
# Plugin Discovery
# ============================================================================

def _iter_provider_dirs() -> List[Tuple[str, Path]]:
    dirs: List[Tuple[str, Path]] = []
    seen: set = set()

    if _PLUGINS_DIR.is_dir():
        for child in sorted(_PLUGINS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(("_", ".")):
                continue
            if child.name == "__pycache__":
                continue
            if not (child / "__init__.py").exists():
                continue
            seen.add(child.name)
            dirs.append((child.name, child))

    if _USER_PLUGINS_DIR.is_dir():
        for child in sorted(_USER_PLUGINS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(("_", ".")):
                continue
            if child.name in seen:
                continue
            if not (child / "__init__.py").exists():
                continue
            dirs.append((child.name, child))

    return dirs


def _is_memory_provider_dir(path: Path) -> bool:
    init_file = path / "__init__.py"
    if not init_file.exists():
        return False
    try:
        source = init_file.read_text(errors="replace")[:8192]
        return "register_memory_provider" in source or "MemoryProvider" in source
    except Exception:
        return False


def _load_pluginmanager_memory_providers() -> Dict[str, "MemoryProvider"]:
    """Try to get memory providers from PluginManager registration path."""
    try:
        from plugins import get_plugin_manager
        pm = get_plugin_manager()
        pm.discover_and_load()
        return pm.get_memory_providers()
    except Exception as e:
        logger.debug(f"PluginManager memory provider load failed: {e}")
        return {}


def discover_memory_providers() -> List[Tuple[str, bool, str]]:
    """Discover all installed memory providers.

    Returns:
        List of (name, is_available, path) tuples
    """
    global _discovered

    if _discovered is not None:
        results = []
        # Merge with PluginManager registry
        pm_providers = _load_pluginmanager_memory_providers()
        seen_names: set = set()
        for n, p in _discovered:
            seen_names.add(n)
            provider = pm_providers.get(n) or _load_provider_from_dir(n, p)
            if provider:
                try:
                    available = provider.is_available()
                except Exception as e:
                    available = False
                    logger.debug(f"Provider {n} is_available() failed: {e}")
            else:
                available = False
            results.append((n, available, str(p)))
        for n, provider in pm_providers.items():
            if n not in seen_names:
                try:
                    available = provider.is_available()
                except Exception:
                    available = False
                results.append((n, available, f"plugin://{n}"))
        return results

    _discovered = []
    results: List[Tuple[str, bool, str]] = []

    for name, path in _iter_provider_dirs():
        _discovered.append((name, path))
        provider = _load_provider_from_dir(name, path)
        if provider:
            try:
                available = provider.is_available()
            except Exception as e:
                available = False
                logger.debug(f"Provider {name} is_available() failed: {e}")
        else:
            available = False
        results.append((name, available, str(path)))

    # Also surface PluginManager-registered providers
    pm_providers = _load_pluginmanager_memory_providers()
    pm_discovered_paths: List[Tuple[str, Path]] = []
    for n, provider in pm_providers.items():
        found = any(dn == n for dn, _ in (_discovered or []))
        if found:
            continue
        try:
            available = provider.is_available()
        except Exception:
            available = False
        results.append((n, available, f"plugin://{n}"))
        pm_discovered_paths.append((n, Path(f"plugin://{n}")))
    if pm_discovered_paths and _discovered is not None:
        _discovered.extend(pm_discovered_paths)

    return results


def find_provider_dir(name: str) -> Optional[Path]:
    global _discovered

    if _discovered is None:
        discover_memory_providers()

    for n, path in _discovered or []:
        if n == name:
            if str(path).startswith("plugin://"):
                return None
            return path

    return None


# ============================================================================
# Plugin Loading
# ============================================================================

def _load_provider_from_dir(name: str, path: Optional[Path] = None) -> Optional["MemoryProvider"]:
    if path is None:
        path = find_provider_dir(name)
    if not path:
        return None

    is_bundled = str(_PLUGINS_DIR) in str(path) or path.parent == _PLUGINS_DIR
    module_name = f"plugins.memory.{name}" if is_bundled else f"_agentz_user_memory.{name}"

    try:
        if module_name in sys.modules:
            mod = sys.modules[module_name]
        else:
            spec = importlib.util.spec_from_file_location(
                module_name,
                path / "__init__.py"
            )
            if spec is None or spec.loader is None:
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)

        if hasattr(mod, "register"):
            ctx = _LegacyPluginContext(name)
            mod.register(ctx)
            if ctx.provider:
                return ctx.provider

        from agent.memory.memory_provider import MemoryProvider

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name, None)
            if (isinstance(attr, type) and
                issubclass(attr, MemoryProvider) and
                attr is not MemoryProvider):
                return attr()

        return None

    except Exception as e:
        logger.warning(f"Failed to load memory provider '{name}': {e}")
        return None


def load_memory_provider(name: str) -> Optional["MemoryProvider"]:
    """Load and return a MemoryProvider instance by name.

    Checks PluginManager registry first, then falls back to direct dir loading.
    """
    if name in _loaded_providers:
        return _loaded_providers[name]

    pm_providers = _load_pluginmanager_memory_providers()
    provider = pm_providers.get(name)
    if provider is not None:
        _loaded_providers[name] = provider
        logger.info(f"Loaded memory provider (via PluginManager): {name}")
        return provider

    path = find_provider_dir(name)
    provider = _load_provider_from_dir(name, path)
    if provider:
        _loaded_providers[name] = provider
        logger.info(f"Loaded memory provider: {name}")

    return provider


def reload_memory_providers() -> None:
    global _discovered, _loaded_providers
    _discovered = None
    _loaded_providers = {}
    try:
        from plugins import get_plugin_manager
        get_plugin_manager().discover_and_load(force=True)
    except Exception:
        pass
    discover_memory_providers()


def is_provider_available(name: str) -> bool:
    provider = load_memory_provider(name)
    if not provider:
        return False
    try:
        return provider.is_available()
    except Exception:
        return False


# ============================================================================
# Provider Diagnostics
# ============================================================================

def diagnose_provider(name: str, force_refresh: bool = False) -> ProviderDiagnostics:
    global _diagnostics_cache

    import time

    if not force_refresh and name in _diagnostics_cache:
        cached = _diagnostics_cache[name]
        if cached.last_check and (time.time() - cached.last_check) < 60:
            return cached

    diagnostics = ProviderDiagnostics(
        name=name,
        status=ProviderStatus.NOT_FOUND,
        last_check=time.time(),
    )

    try:
        pm_providers = _load_pluginmanager_memory_providers()
        provider: Optional["MemoryProvider"] = pm_providers.get(name)
        path: Optional[str] = None

        if provider is None:
            path_obj = find_provider_dir(name)
            if path_obj:
                path = str(path_obj)
                provider = _load_provider_from_dir(name, path_obj)

        if provider is None:
            diagnostics.status = ProviderStatus.NOT_FOUND
            diagnostics.error = f"Provider '{name}' not found in plugin directories"
            _diagnostics_cache[name] = diagnostics
            return diagnostics

        diagnostics.path = path or f"plugin://{name}"
        diagnostics.status = ProviderStatus.LOADED

        try:
            diagnostics.is_available = provider.is_available()
            if diagnostics.is_available:
                diagnostics.status = ProviderStatus.AVAILABLE
            else:
                diagnostics.status = ProviderStatus.FOUND_BUT_UNAVAILABLE
                diagnostics.warnings.append("Provider reported itself as unavailable")
        except Exception as e:
            diagnostics.status = ProviderStatus.FOUND_BUT_UNAVAILABLE
            diagnostics.error = str(e)
            diagnostics.error_type = "availability_check_failed"

        try:
            for schema in provider.get_tool_schemas():
                tool_name = schema.get("name")
                if tool_name:
                    diagnostics.available_tools.append(tool_name)
        except Exception as e:
            diagnostics.warnings.append(f"Failed to get tool schemas: {e}")

        try:
            diagnostics.config_schema = provider.get_config_schema()
        except Exception as e:
            diagnostics.warnings.append(f"Failed to get config schema: {e}")

        _check_provider_warnings(provider, diagnostics)

    except Exception as e:
        diagnostics.status = ProviderStatus.ERROR
        diagnostics.error = str(e)
        diagnostics.error_type = type(e).__name__

    _diagnostics_cache[name] = diagnostics
    return diagnostics


def diagnose_all_providers(force_refresh: bool = False) -> Dict[str, ProviderDiagnostics]:
    results = {}

    results["builtin"] = ProviderDiagnostics(
        name="builtin",
        status=ProviderStatus.AVAILABLE,
        path="built-in",
        is_available=True,
        available_tools=["memory"],
        last_check=None,
    )

    for name, _, path in discover_memory_providers():
        results[name] = diagnose_provider(name, force_refresh=force_refresh)

    return results


def _check_provider_warnings(provider: "MemoryProvider", diagnostics: ProviderDiagnostics) -> None:
    from agent.memory.memory_provider import MemoryProvider

    if not hasattr(provider, 'name') or not provider.name:
        diagnostics.warnings.append("Provider missing or empty 'name' property")

    required_methods = ['is_available', 'initialize', 'get_tool_schemas', 'system_prompt_block']
    for method in required_methods:
        if not hasattr(provider, method):
            diagnostics.warnings.append(f"Provider missing required method: {method}")

    try:
        schemas = provider.get_tool_schemas()
        for schema in schemas:
            if not isinstance(schema, dict):
                diagnostics.warnings.append("Tool schema is not a dict")
                continue
            if 'name' not in schema:
                diagnostics.warnings.append("Tool schema missing 'name' field")
    except Exception as e:
        diagnostics.warnings.append(f"Error checking tool schemas: {e}")


# ============================================================================
# Provider Configuration Validation
# ============================================================================

def validate_provider_config(
    provider_name: str,
    config: Dict[str, Any],
    strict: bool = True,
) -> ProviderValidationResult:
    result = ProviderValidationResult(provider_name=provider_name, is_valid=True)

    if provider_name == "builtin":
        return result

    provider = load_memory_provider(provider_name)
    if not provider:
        result.is_valid = False
        result.errors.append(f"Provider '{provider_name}' not found or failed to load")
        available = discover_memory_providers()
        if available:
            names = [n for n, _, _ in available]
            result.suggestions.append(f"Available providers: {', '.join(names)}")
        return result

    try:
        schema = provider.get_config_schema()
    except Exception as e:
        result.warnings.append(f"Failed to get config schema: {e}")
        schema = []

    if not schema:
        return result

    required_fields = [f.get('key') for f in schema if f.get('required')]
    for field_name in required_fields:
        if field_name not in config or config.get(field_name) is None:
            result.is_valid = False
            result.errors.append(f"Missing required field: '{field_name}'")
            for f in schema:
                if f.get('key') == field_name:
                    desc = f.get('description', 'No description')
                    result.suggestions.append(f"'{field_name}': {desc}")
                    break

    for field_def in schema:
        key = field_def.get('key')
        if key not in config:
            if not field_def.get('required') and strict:
                result.warnings.append(f"Optional field missing: '{key}'")
            continue

        value = config.get(key)

        if 'choices' in field_def:
            choices = field_def['choices']
            if value not in choices:
                result.is_valid = False
                result.errors.append(
                    f"Invalid value for '{key}': '{value}'. Must be one of: {choices}"
                )

        if field_def.get('url') and value:
            if not _is_valid_url(str(value)):
                result.errors.append(f"'{key}' is not a valid URL")

        if isinstance(value, str) and value.lower() in ('true', 'false'):
            result.warnings.append(f"'{key}' should be boolean, not string")

    _validate_provider_specific(provider_name, config, result)

    return result


def _validate_provider_specific(
    provider_name: str,
    config: Dict[str, Any],
    result: ProviderValidationResult,
) -> None:
    if provider_name == "honcho":
        if 'api_key' in config and config['api_key']:
            key = config['api_key']
            if len(key) < 20:
                result.warnings.append("API key appears to be too short")
            if not (key.startswith('sk-') or key.startswith('hk-')):
                pass  # reasonable but flexible format

    if provider_name == "mem0":
        if 'api_key' in config and not config['api_key']:
            result.errors.append("Mem0 requires an API key")
        if 'organization_id' not in config:
            result.warnings.append("Consider setting organization_id for better tracking")


def _is_valid_url(url: str) -> bool:
    import re
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))


def validate_all_configs(configs: Dict[str, Dict[str, Any]]) -> Dict[str, ProviderValidationResult]:
    results = {}
    for name, config in configs.items():
        results[name] = validate_provider_config(name, config)
    return results


# ============================================================================
# Provider Errors
# ============================================================================

class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        provider_name: str = "",
        error_type: str = "unknown",
        recoverable: bool = True,
        suggestion: str = "",
    ):
        super().__init__(message)
        self.provider_name = provider_name
        self.error_type = error_type
        self.recoverable = recoverable
        self.suggestion = suggestion


class ProviderNotFoundError(ProviderError):
    def __init__(self, provider_name: str, suggestion: str = ""):
        super().__init__(
            f"Memory provider '{provider_name}' not found",
            provider_name=provider_name,
            error_type="not_found",
            recoverable=False,
            suggestion=suggestion,
        )


class ProviderLoadError(ProviderError):
    def __init__(self, provider_name: str, original_error: Exception):
        super().__init__(
            f"Failed to load memory provider '{provider_name}': {original_error}",
            provider_name=provider_name,
            error_type="load_error",
            recoverable=False,
            suggestion=f"Check if '{provider_name}' is properly installed",
        )


class ProviderUnavailableError(ProviderError):
    def __init__(self, provider_name: str, reason: str = ""):
        super().__init__(
            f"Memory provider '{provider_name}' is not available" + (f": {reason}" if reason else ""),
            provider_name=provider_name,
            error_type="unavailable",
            recoverable=True,
            suggestion="Check provider configuration and credentials",
        )


class ProviderConfigError(ProviderError):
    def __init__(self, provider_name: str, errors: List[str]):
        error_msg = f"Configuration errors for '{provider_name}': " + "; ".join(errors)
        super().__init__(
            error_msg,
            provider_name=provider_name,
            error_type="config_invalid",
            recoverable=True,
            suggestion="Review configuration and fix errors",
        )


def handle_provider_error(
    error: Exception,
    provider_name: str = "",
    fallback: str = "builtin",
) -> Tuple[bool, Optional["MemoryProvider"], str]:
    from agent.memory.memory_provider import BuiltinMemoryProvider

    if isinstance(error, ProviderNotFoundError):
        logger.warning(f"Provider '{provider_name}' not found, falling back to builtin")
        builtin = BuiltinMemoryProvider()
        return True, builtin, f"Provider '{provider_name}' not found, using builtin"

    if isinstance(error, ProviderUnavailableError):
        logger.warning(f"Provider '{provider_name}' unavailable: {error}, falling back to builtin")
        builtin = BuiltinMemoryProvider()
        return True, builtin, f"Provider '{provider_name}' unavailable, using builtin"

    if isinstance(error, ProviderConfigError):
        logger.error(f"Provider '{provider_name}' configuration error: {error}")
        return False, None, str(error)

    if isinstance(error, ProviderLoadError):
        logger.error(f"Provider '{provider_name}' load error: {error}")
        return False, None, str(error)

    logger.error(f"Unexpected error with provider '{provider_name}': {error}")
    try:
        builtin = BuiltinMemoryProvider()
        return True, builtin, f"Unexpected error: {error}, using builtin"
    except Exception:
        return False, None, f"Critical error: {error}"


# ============================================================================
# Health Check
# ============================================================================

def health_check_provider(name: str) -> Dict[str, Any]:
    import time

    result = {
        "name": name,
        "healthy": False,
        "checks": {},
        "timestamp": time.time(),
    }

    try:
        provider = load_memory_provider(name)
        result["checks"]["load"] = {
            "passed": provider is not None,
            "error": None if provider else "Failed to load",
        }

        if not provider:
            return result

        try:
            is_available = provider.is_available()
            result["checks"]["availability"] = {
                "passed": is_available,
                "error": None if is_available else "Provider reported unavailable",
            }
        except Exception as e:
            result["checks"]["availability"] = {
                "passed": False,
                "error": str(e),
            }

        try:
            schemas = provider.get_tool_schemas()
            result["checks"]["tools"] = {
                "passed": True,
                "tool_count": len(schemas),
                "tools": [s.get("name") for s in schemas if s.get("name")],
            }
        except Exception as e:
            result["checks"]["tools"] = {
                "passed": False,
                "error": str(e),
            }

        result["healthy"] = all(
            check.get("passed", False) for check in result["checks"].values()
        )

    except Exception as e:
        result["error"] = str(e)

    return result


# ============================================================================
# CLI Integration
# ============================================================================

def discover_plugin_cli_commands(provider_name: Optional[str] = None) -> List[Dict]:
    commands = []
    providers = discover_memory_providers()

    for name, available, path in providers:
        if provider_name and name != provider_name:
            continue
        if not available:
            continue
        if str(path).startswith("plugin://"):
            continue
        cli_file = Path(path) / "cli.py"
        if not cli_file.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"_cli_{name}", cli_file)
            if spec and spec.loader:
                cli_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cli_mod)
                register_cli = getattr(cli_mod, "register_cli", None)
                if register_cli and callable(register_cli):
                    cmd = register_cli()
                    if cmd:
                        commands.append({
                            "name": name,
                            "command": cmd
                        })
        except Exception as e:
            logger.debug(f"Failed to load CLI for {name}: {e}")

    return commands


# ============================================================================
# Provider Registry Helpers
# ============================================================================

def get_active_provider_name() -> str:
    try:
        from common.config import settings
        return getattr(settings, "memory_provider", "builtin")
    except Exception:
        return "builtin"


def get_provider_choices() -> List[Dict]:
    choices = [
        {"name": "builtin", "available": True, "path": "built-in"}
    ]

    for name, available, path in discover_memory_providers():
        choices.append({
            "name": name,
            "available": available,
            "path": path
        })

    return choices


__all__ = [
    "discover_memory_providers",
    "load_memory_provider",
    "find_provider_dir",
    "is_provider_available",
    "reload_memory_providers",
    "diagnose_provider",
    "diagnose_all_providers",
    "health_check_provider",
    "validate_provider_config",
    "validate_all_configs",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderLoadError",
    "ProviderUnavailableError",
    "ProviderConfigError",
    "handle_provider_error",
    "ProviderStatus",
    "ProviderDiagnostics",
    "ProviderValidationResult",
    "_LegacyPluginContext",
    "discover_plugin_cli_commands",
    "get_active_provider_name",
    "get_provider_choices",
]
