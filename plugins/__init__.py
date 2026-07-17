"""
Agent-Z Plugin System
=====================

Discovers, loads, and manages plugins from four sources:

1. **Bundled plugins** – ``<repo>/plugins/<name>/`` (shipped with Agent-Z;
   ``memory/`` and ``context_engine/`` subdirs are excluded — they have their
   own discovery paths)
2. **User plugins**   – ``~/.agent_z/plugins/<name>/``
3. **Project plugins** – ``./.agent_z/plugins/<name>/`` (opt-in via
   ``AGENT_Z_ENABLE_PROJECT_PLUGINS``)
4. **Pip plugins**     – packages that expose the ``agent_z.plugins``
   entry-point group.

Later sources override earlier ones on name collision, so a user or project
plugin with the same name as a bundled plugin replaces it.

Each directory plugin must contain a ``plugin.yaml`` manifest **and** an
``__init__.py`` with a ``register(ctx)`` function.

Lifecycle hooks
---------------
Plugins may register callbacks for any of the hooks in ``VALID_HOOKS``.
The agent core calls ``invoke_hook(name, **kwargs)`` at the appropriate
points.

Tool registration
-----------------
``PluginContext.register_tool()`` delegates to ``tools.registry.register()``
so plugin-defined tools appear alongside the built-in tools.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import inspect
import os
import sys
import threading
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from common.config import AGENT_Z_HOME
from common.logging_manager import get_system_logger


def get_bundled_plugins_dir() -> Path:
    """Locate the bundled ``plugins/`` directory.

    Honours ``AGENT_Z_BUNDLED_PLUGINS`` so read-only store paths are
    consulted first.  Falls back to the in-repo path used during development.
    """
    env_override = os.getenv("AGENT_Z_BUNDLED_PLUGINS")
    if env_override:
        return Path(env_override)
    return Path(__file__).resolve().parent


try:
    import yaml
except ImportError:  # pragma: no cover – yaml is optional at import time
    yaml = None  # type: ignore[assignment]


def _fast_safe_load(text: str) -> Any:
    """Safe YAML loader wrapper – mirrors Hermes' fast_safe_load helper."""
    if yaml is None:
        return None
    try:
        return yaml.safe_load(text) or {}
    except Exception:
        return None


class PluginToolOverrideError(PermissionError):
    """Raised when a plugin attempts to override a built-in tool without
    operator opt-in via ``plugins.entries.<plugin_id>.allow_tool_override``.
    """


logger = get_system_logger("PluginSystem")

# ---------------------------------------------------------------------------
# Plugin developer debug logging
# ---------------------------------------------------------------------------
#
# Set ``AGENT_Z_PLUGINS_DEBUG=1`` to surface verbose plugin-discovery logs to
# stderr in addition to ~/.agent_z/logs/agent.log. Aimed at plugin authors
# trying to figure out why their plugin isn't showing up.

_PLUGINS_DEBUG = os.getenv("AGENT_Z_PLUGINS_DEBUG", "").strip().lower() in {
    "1", "true", "yes", "on",
}
_DEBUG_HANDLER_INSTALLED = False


def _install_plugin_debug_handler(force: bool = False) -> None:
    """When AGENT_Z_PLUGINS_DEBUG is on, tee plugin logs to stderr at DEBUG.

    Idempotent: only attaches the handler once per process unless ``force``
    is passed. Does not touch the root logger or other Agent-Z loggers.
    """
    global _DEBUG_HANDLER_INSTALLED, _PLUGINS_DEBUG
    if force:
        _PLUGINS_DEBUG = os.getenv("AGENT_Z_PLUGINS_DEBUG", "").strip().lower() in {
            "1", "true", "yes", "on",
        }
    if not _PLUGINS_DEBUG or _DEBUG_HANDLER_INSTALLED:
        return
    import logging as _logging
    handler = _logging.StreamHandler(sys.stderr)
    handler.setLevel(_logging.DEBUG)
    handler.setFormatter(_logging.Formatter("[plugins] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(_logging.DEBUG)
    logger.propagate = True
    _DEBUG_HANDLER_INSTALLED = True
    logger.debug(
        "AGENT_Z_PLUGINS_DEBUG=1 — verbose plugin discovery logging enabled"
    )


_install_plugin_debug_handler()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_HOOKS: Set[str] = {
    "pre_tool_call",
    "post_tool_call",
    "transform_terminal_output",
    "transform_tool_result",
    "transform_llm_output",
    "pre_llm_call",
    "post_llm_call",
    "pre_verify",
    "pre_api_request",
    "post_api_request",
    "api_request_error",
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
    "subagent_start",
    "subagent_stop",
    "pre_gateway_dispatch",
    "pre_approval_request",
    "post_approval_response",
    "kanban_task_claimed",
    "kanban_task_completed",
    "kanban_task_blocked",
}

VALID_MIDDLEWARE: Set[str] = {
    "observer",
    "api_request",
    "completion",
}

ENTRY_POINTS_GROUP = "agent_z.plugins"

_NS_PARENT = "agentz_plugins"


def _env_enabled(name: str) -> bool:
    """Return True when an env var is set to a truthy opt-in value."""
    val = os.getenv(name, "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def _get_disabled_plugins() -> set:
    """Read the disabled plugins list from config.yaml."""
    try:
        from common.config import load_config, cfg_get
        config = load_config()
        disabled = cfg_get(config, "plugins", "disabled", default=[])
        return set(disabled) if isinstance(disabled, list) else set()
    except Exception:
        return set()


def _get_enabled_plugins() -> Optional[set]:
    """Read the enabled-plugins allow-list from config.yaml.

    Plugins are opt-in by default — only plugins whose name appears in
    this set are loaded. Returns:
        None  — key is missing; treat as "nothing enabled yet".
        set() — explicitly empty; nothing loads.
        set(...) — the concrete allow-list.
    """
    try:
        from common.config import load_config
        config = load_config()
        plugins_cfg = config.get("plugins")
        if not isinstance(plugins_cfg, dict):
            return None
        if "enabled" not in plugins_cfg:
            return None
        enabled = plugins_cfg.get("enabled")
        if not isinstance(enabled, list):
            return None
        return set(enabled)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

_VALID_PLUGIN_KINDS: Set[str] = {
    "standalone",
    "backend",
    "exclusive",
    "platform",
    "model-provider",
}


@dataclass
class PluginManifest:
    """Parsed representation of a plugin.yaml manifest."""

    name: str
    version: str = ""
    description: str = ""
    author: str = ""
    requires_env: List[Union[str, Dict[str, Any]]] = field(default_factory=list)
    provides_tools: List[str] = field(default_factory=list)
    provides_hooks: List[str] = field(default_factory=list)
    source: str = ""        # "user", "project", or "entrypoint"
    path: Optional[str] = None
    kind: str = "standalone"
    key: str = ""


@dataclass
class LoadedPlugin:
    """Runtime state for a single loaded plugin."""

    manifest: PluginManifest
    module: Optional[types.ModuleType] = None
    tools_registered: List[str] = field(default_factory=list)
    hooks_registered: List[str] = field(default_factory=list)
    middleware_registered: List[str] = field(default_factory=list)
    commands_registered: List[str] = field(default_factory=list)
    enabled: bool = False
    error: Optional[str] = None
    deferred: bool = False


# ---------------------------------------------------------------------------
# PluginContext  – handed to each plugin's ``register()`` function
# ---------------------------------------------------------------------------

class PluginContext:
    """Facade given to plugins so they can register tools and hooks."""

    def __init__(self, manifest: PluginManifest, manager: "PluginManager"):
        self.manifest = manifest
        self._manager = manager
        self._llm: Any = None

    # -- host-owned LLM access ----------------------------------------------

    @property
    def llm(self) -> Any:
        """Return the plugin's LLM facade for running host-owned completions."""
        if self._llm is None:
            from agent.llm.llm_client import LLMClient
            from common.config import settings
            plugin_id = self.manifest.key or self.manifest.name
            try:
                self._llm = LLMClient(
                    provider=settings.model_settings.provider or "openai",
                    model=settings.model_settings.model or "",
                )
            except Exception:
                self._llm = None
        return self._llm

    # -- profile awareness --------------------------------------------------

    @property
    def profile_name(self) -> str:
        """Return the active Agent-Z profile name."""
        try:
            from common.config import get_active_profile_name
            return get_active_profile_name()
        except Exception:
            return "default"

    # -- tool registration --------------------------------------------------

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable | None = None,
        requires_env: list | None = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        override: bool = False,
    ) -> None:
        """Register a tool in the global registry **and** track it as plugin-provided."""
        if override and not self._tool_override_allowed(name):
            plugin_id = self.manifest.key or self.manifest.name
            raise PluginToolOverrideError(
                f"Plugin {self.manifest.name!r} cannot override built-in tool "
                f"{name!r}. Set "
                f"plugins.entries.{plugin_id}.allow_tool_override: true "
                f"in config.yaml to allow this plugin to replace built-in tools."
            )

        from tools.registry import registry

        registry.register(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env,
            is_async=is_async,
            description=description,
            emoji=emoji,
        )
        self._manager._plugin_tool_names.add(name)
        logger.debug(
            "Plugin %s registered tool: %s%s",
            self.manifest.name, name, " (override)" if override else "",
        )

    # -- override trust gate ------------------------------------------------

    def _tool_override_allowed(self, tool_name: str) -> bool:
        """Return True if this plugin is configured to override built-in tools."""
        source = getattr(self.manifest, "source", "") or ""
        if source == "bundled":
            return True
        try:
            from common.config import load_config
            cfg = load_config() or {}
        except Exception:
            return False
        plugin_id = self.manifest.key or self.manifest.name
        entries = (cfg.get("plugins") or {}).get("entries") or {}
        entry = entries.get(plugin_id) or {}
        return bool(entry.get("allow_tool_override", False))

    # -- message injection --------------------------------------------------

    def inject_message(self, content: str, role: str = "user") -> bool:
        """Inject a message into the active conversation."""
        cli = self._manager._cli_ref
        if cli is None:
            logger.warning("inject_message: no CLI reference")
            return False

        msg = content if role == "user" else f"[{role}] {content}"

        if getattr(cli, "_agent_running", False):
            cli._interrupt_queue.put(msg)
        else:
            cli._pending_input.put(msg)
        return True

    # -- CLI command registration ------------------------------------------

    def register_cli_command(
        self,
        name: str,
        help: str,
        setup_fn: Callable,
        handler_fn: Callable | None = None,
        description: str = "",
    ) -> None:
        """Register a CLI subcommand (e.g. ``agentz honcho ...``)."""
        self._manager._cli_commands[name] = {
            "name": name,
            "help": help,
            "description": description,
            "setup_fn": setup_fn,
            "handler_fn": handler_fn,
            "plugin": self.manifest.name,
        }
        logger.debug("Plugin %s registered CLI command: %s", self.manifest.name, name)

    # -- slash command registration -----------------------------------------

    def register_command(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        args_hint: str = "",
    ) -> None:
        """Register a slash command (e.g. ``/lcm``) available in CLI and gateway sessions."""
        clean = name.lower().strip().lstrip("/").replace(" ", "-")
        if not clean:
            logger.warning(
                "Plugin '%s' tried to register a command with an empty name.",
                self.manifest.name,
            )
            return
        self._manager._plugin_commands[clean] = {
            "handler": handler,
            "description": description or "Plugin command",
            "plugin": self.manifest.name,
            "args_hint": (args_hint or "").strip(),
        }
        logger.debug("Plugin %s registered command: /%s", self.manifest.name, clean)

    # -- tool dispatch ------------------------------------------------------

    def dispatch_tool(self, tool_name: str, args: dict, **kwargs) -> str:
        """Dispatch a tool call through the registry, with parent agent context."""
        from tools.registry import registry

        if "parent_agent" not in kwargs:
            cli = self._manager._cli_ref
            agent = getattr(cli, "agent", None) if cli else None
            if agent is not None:
                kwargs["parent_agent"] = agent

        return registry.dispatch(tool_name, args, **kwargs)

    # -- provider registration ---------------------------------------------

    def register_memory_provider(self, provider) -> None:
        """Register a memory provider plugin."""
        from agent.memory.memory_provider import MemoryProvider

        if not isinstance(provider, MemoryProvider):
            logger.warning(
                "Plugin '%s' tried to register a memory provider that does "
                "not inherit from MemoryProvider. Ignoring.",
                self.manifest.name,
            )
            return
        self._manager._memory_providers[provider.name] = provider
        logger.info(
            "Plugin '%s' registered memory provider: %s",
            self.manifest.name, provider.name,
        )

    def register_context_engine(self, engine) -> None:
        """Register a context engine to replace the built-in ContextCompressor."""
        if self._manager._context_engine is not None:
            logger.warning(
                "Plugin '%s' tried to register a context engine, but one is "
                "already registered. Only one context engine plugin is allowed.",
                self.manifest.name,
            )
            return
        from agent.context.context_engine import ContextEngine
        if not isinstance(engine, ContextEngine):
            logger.warning(
                "Plugin '%s' tried to register a context engine that does "
                "not inherit from ContextEngine. Ignoring.",
                self.manifest.name,
            )
            return
        self._manager._context_engine = engine
        self._manager._context_engines[getattr(engine, "name", self.manifest.name)] = engine
        logger.info(
            "Plugin '%s' registered context engine: %s",
            self.manifest.name, engine.name,
        )

    def register_model_provider(self, provider) -> None:
        """Register a model provider profile."""
        try:
            from agent.llm.factory import register_provider
            register_provider(provider)
            name = getattr(provider, "name", self.manifest.name)
            self._manager._model_providers[name] = provider
            logger.info(
                "Plugin '%s' registered model provider: %s",
                self.manifest.name, name,
            )
        except Exception as e:
            logger.warning(
                "Plugin '%s' failed to register model provider: %s",
                self.manifest.name, e,
            )

    def register_web_search_provider(self, provider) -> None:
        """Register a web search backend."""
        try:
            from agent.llm.llm_web_search import register_search_provider
            register_search_provider(provider)
            name = getattr(provider, "name", self.manifest.name)
            self._manager._web_search_backends[name] = provider
            logger.info(
                "Plugin '%s' registered web search provider: %s",
                self.manifest.name, name,
            )
        except Exception as e:
            logger.warning(
                "Plugin '%s' failed to register web search provider: %s",
                self.manifest.name, e,
            )

    def register_skill(
        self,
        name: str,
        path: Path,
        description: str = "",
    ) -> None:
        """Register a read-only skill provided by this plugin."""
        import re
        _NAMESPACE_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

        if ":" in name:
            raise ValueError(
                f"Skill name '{name}' must not contain ':' "
                f"(the namespace is derived from the plugin name "
                f"'{self.manifest.name}' automatically)."
            )
        if not name or not _NAMESPACE_RE.match(name):
            raise ValueError(
                f"Invalid skill name '{name}'. Must match [a-zA-Z0-9_-]+."
            )
        if not path.exists():
            raise FileNotFoundError(f"SKILL.md not found at {path}")

        qualified = f"{self.manifest.name}:{name}"
        self._manager._plugin_skills[qualified] = {
            "path": path,
            "plugin": self.manifest.name,
            "bare_name": name,
            "description": description,
        }
        logger.debug(
            "Plugin %s registered skill: %s",
            self.manifest.name, qualified,
        )

    def register_auxiliary_task(
        self,
        key: str,
        *,
        display_name: str,
        description: str,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a plugin-defined auxiliary LLM task."""
        if not key or not isinstance(key, str):
            raise ValueError(
                f"Plugin '{self.manifest.name}' tried to register auxiliary task "
                f"with invalid key {key!r}"
            )
        if not all(c.isalnum() or c == "_" for c in key):
            raise ValueError(
                f"Plugin '{self.manifest.name}' auxiliary task key {key!r} "
                f"must contain only alphanumeric characters and underscores"
            )
        existing = self._manager._aux_tasks.get(key)
        if existing is not None and existing.get("plugin") != self.manifest.name:
            raise ValueError(
                f"Plugin '{self.manifest.name}' cannot register auxiliary task "
                f"{key!r} — already registered by plugin "
                f"'{existing.get('plugin')}'"
            )
        merged_defaults: Dict[str, Any] = {
            "provider": "auto",
            "model": "",
            "base_url": "",
            "api_key": "",
            "timeout": 60,
            "extra_body": {},
        }
        if defaults:
            for k, v in defaults.items():
                merged_defaults[k] = v

        self._manager._aux_tasks[key] = {
            "key": key,
            "display_name": display_name,
            "description": description,
            "defaults": merged_defaults,
            "plugin": self.manifest.name,
        }
        logger.debug(
            "Plugin %s registered auxiliary task: %s (%s)",
            self.manifest.name,
            key,
            display_name,
        )

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register a lifecycle hook callback."""
        if hook_name not in VALID_HOOKS:
            logger.warning(
                "Plugin '%s' registered unknown hook '%s' "
                "(valid: %s)",
                self.manifest.name,
                hook_name,
                ", ".join(sorted(VALID_HOOKS)),
            )
        self._manager._hooks.setdefault(hook_name, []).append(callback)
        logger.debug("Plugin %s registered hook: %s", self.manifest.name, hook_name)

    def register_middleware(self, kind: str, callback: Callable) -> None:
        """Register a behavior-changing middleware callback."""
        if kind not in VALID_MIDDLEWARE:
            logger.warning(
                "Plugin '%s' registered unknown middleware '%s' "
                "(valid: %s)",
                self.manifest.name,
                kind,
                ", ".join(sorted(VALID_MIDDLEWARE)),
            )
        self._manager._middleware.setdefault(kind, []).append(callback)
        logger.debug("Plugin %s registered middleware: %s", self.manifest.name, kind)


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------

class PluginManager:
    """Central manager that discovers, loads, and invokes plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._load_errors: Dict[str, str] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._middleware: Dict[str, List[Callable]] = {}
        self._plugin_tool_names: Set[str] = set()
        self._plugin_platform_names: Set[str] = set()
        self._cli_commands: Dict[str, dict] = {}
        self._context_engine = None
        self._plugin_commands: Dict[str, dict] = {}
        self._discovered: bool = False
        self._cli_ref = None
        self._plugin_skills: Dict[str, Dict[str, Any]] = {}
        self._aux_tasks: Dict[str, Dict[str, Any]] = {}
        self._slack_action_handlers: List[tuple] = []
        self._memory_providers: Dict[str, Any] = {}
        self._context_engines: Dict[str, Any] = {}
        self._model_providers: Dict[str, Any] = {}
        self._web_search_backends: Dict[str, Any] = {}
        self._tool_providers: Dict[str, Any] = {}

    # -----------------------------------------------------------------------
    # Public
    # -----------------------------------------------------------------------

    def set_cli_ref(self, cli: Any) -> None:
        """Attach a reference to the active CLI session."""
        self._cli_ref = cli

    # --- Hook / middleware dispatch ---------------------------------------

    def emit_hook_event(self, hook_name: str, **kwargs: Any) -> List[Any]:
        """Invoke all registered callbacks for ``hook_name``.

        Any callback that raises an exception is logged and skipped so that
        later callbacks still execute.  Returns a list of return values from
        callbacks that completed without raising.
        """
        if hook_name not in VALID_HOOKS:
            logger.warning(
                "emit_hook_event: unknown hook '%s' (valid: %s)",
                hook_name,
                ", ".join(sorted(VALID_HOOKS)),
            )
        results: List[Any] = []
        callbacks = list(self._hooks.get(hook_name, ()))
        if not callbacks:
            return results
        logger.debug("Emitting hook '%s' to %d callback(s)", hook_name, len(callbacks))
        for cb in callbacks:
            try:
                res = cb(**kwargs)
                results.append(res)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "Hook callback for '%s' raised: %s (callback=%s)",
                    hook_name,
                    exc,
                    getattr(cb, "__name__", repr(cb)),
                )
        return results

    # Alias for convenience (Hermes style)
    fire = emit_hook_event

    def run_middleware(self, kind: str, initial: Any, **kwargs: Any) -> Any:
        """Run a middleware chain, threading the result through each callback.

        Each callback receives the current value as first positional argument
        plus any extra kwargs, and returns the (possibly) transformed value.
        """
        if kind not in VALID_MIDDLEWARE:
            logger.warning(
                "run_middleware: unknown middleware '%s' (valid: %s)",
                kind,
                ", ".join(sorted(VALID_MIDDLEWARE)),
            )
        value = initial
        for cb in self._middleware.get(kind, ()):
            try:
                value = cb(value, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "Middleware '%s' callback raised: %s (skipping)",
                    kind,
                    exc,
                )
        return value

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Convenience top-level hook registration (uses an internal context)."""
        internal_mf = PluginManifest(
            name="__core__",
            version="0.0.0",
            source="core",
            kind="shared",
        )
        ctx = PluginContext(manager=self, manifest=internal_mf, workdir=None,
                            shared_state=self._shared_state())
        ctx.register_hook(hook_name, callback)

    def register_memory_provider(self, provider: Any) -> None:
        """Convenience method to register a memory provider directly."""
        internal_mf = PluginManifest(
            name="__core__",
            version="0.0.0",
            source="core",
            kind="shared",
        )
        ctx = PluginContext(manager=self, manifest=internal_mf, workdir=None,
                            shared_state=self._shared_state())
        ctx.register_memory_provider(provider)

    def _shared_state(self) -> Dict[str, Any]:
        if not hasattr(self, "_core_shared"):
            self._core_shared: Dict[str, Any] = {}
        return self._core_shared

    def discover_and_load(self, force: bool = False, only: Optional[List[str]] = None) -> None:
        """Scan all plugin sources and load each plugin found.

        Args:
            force: If True, discard any existing state and re-scan from scratch.
            only:  Optional list of plugin names. If provided, only plugins whose
                   manifest name is in this list will be loaded (discovery still
                   scans everything).
        """
        if self._discovered and not force:
            if only:
                # Attempt to re-load the requested subset from existing manifests
                for want in only:
                    mf = self._manifests.get(want)
                    if mf and want not in self._plugins:
                        try:
                            self._load_plugin(mf)
                        except Exception as exc:
                            self._load_errors[want] = str(exc)
            return
        if _env_enabled("AGENT_Z_SAFE_MODE"):
            logger.info("AGENT_Z_SAFE_MODE=1 — plugin discovery skipped")
            self._discovered = True
            return
        if force:
            self._plugins.clear()
            self._manifests.clear()
            self._load_errors.clear()
            self._hooks.clear()
            self._middleware.clear()
            self._plugin_tool_names.clear()
            self._plugin_platform_names.clear()
            self._cli_commands.clear()
            self._plugin_commands.clear()
            self._plugin_skills.clear()
            self._aux_tasks.clear()
            self._slack_action_handlers.clear()
            self._context_engine = None
            self._memory_providers.clear()
            self._context_engines.clear()
            self._model_providers.clear()
            self._web_search_backends.clear()
            self._tool_providers.clear()
        self._discovered = True
        try:
            self._discover_and_load_inner(only=only)
        except BaseException:
            self._discovered = False
            raise

    def _discover_and_load_inner(self, only: Optional[List[str]] = None) -> None:
        """The actual discovery sweep."""
        manifests: List[PluginManifest] = []

        repo_plugins = get_bundled_plugins_dir()
        logger.debug("Scanning bundled plugins: %s", repo_plugins)
        bundled = self._scan_directory(
            repo_plugins,
            source="bundled",
            skip_names={"memory", "context_engine", "platforms", "model-providers"},
        )
        logger.debug("  bundled (top-level): %d manifest(s)", len(bundled))
        manifests.extend(bundled)

        user_dir = AGENT_Z_HOME / "plugins"
        logger.debug("Scanning user plugins: %s", user_dir)
        user_manifests = self._scan_directory(user_dir, source="user")
        logger.debug("  user: %d manifest(s)", len(user_manifests))
        manifests.extend(user_manifests)

        if _env_enabled("AGENT_Z_ENABLE_PROJECT_PLUGINS"):
            project_dir = Path.cwd() / ".agent_z" / "plugins"
            logger.debug("Scanning project plugins: %s", project_dir)
            project_manifests = self._scan_directory(project_dir, source="project")
            logger.debug("  project: %d manifest(s)", len(project_manifests))
            manifests.extend(project_manifests)

        ep_manifests = self._scan_entry_points()
        logger.debug("  entrypoints: %d manifest(s)", len(ep_manifests))
        manifests.extend(ep_manifests)

        disabled = _get_disabled_plugins()
        enabled = _get_enabled_plugins()
        winners: Dict[str, PluginManifest] = {}
        for manifest in manifests:
            key = manifest.key or manifest.name
            if not key:
                continue
            winners[key] = manifest
            self._manifests[key] = manifest
            if manifest.name and manifest.name not in self._manifests:
                self._manifests[manifest.name] = manifest

        only_set = set(only) if only else None

        for manifest in winners.values():
            lookup_key = manifest.key or manifest.name

            if only_set is not None and manifest.name not in only_set and lookup_key not in only_set:
                continue

            if lookup_key in disabled or manifest.name in disabled:
                loaded = LoadedPlugin(manifest=manifest, enabled=False)
                loaded.error = "disabled via config"
                self._plugins[lookup_key] = loaded
                logger.debug("Skipping disabled plugin '%s'", lookup_key)
                continue

            if manifest.kind == "exclusive":
                loaded = LoadedPlugin(manifest=manifest, enabled=False)
                loaded.error = (
                    "exclusive plugin — activate via <category>.provider config"
                )
                self._plugins[lookup_key] = loaded
                logger.debug(
                    "Skipping '%s' (exclusive, handled by category discovery)",
                    lookup_key,
                )
                continue

            if manifest.kind == "model-provider":
                loaded = LoadedPlugin(manifest=manifest, enabled=True)
                self._plugins[lookup_key] = loaded
                logger.debug(
                    "Skipping '%s' (model-provider, handled by providers/ discovery)",
                    lookup_key,
                )
                continue

            if manifest.source == "bundled" and manifest.kind == "backend":
                try:
                    self._load_plugin(manifest)
                except Exception as exc:
                    self._load_errors[lookup_key] = str(exc)
                continue

            if manifest.source == "bundled" and manifest.kind == "platform":
                self._register_deferred_platform(manifest)
                continue

            is_enabled = (
                enabled is not None
                and (lookup_key in enabled or manifest.name in enabled)
            )
            if not is_enabled:
                loaded = LoadedPlugin(manifest=manifest, enabled=False)
                loaded.error = (
                    "not enabled in config (run `agentz plugins enable {}` to activate)"
                    .format(lookup_key)
                )
                self._plugins[lookup_key] = loaded
                logger.debug(
                    "Skipping '%s' (not in plugins.enabled)", lookup_key
                )
                continue
            try:
                self._load_plugin(manifest)
            except Exception as exc:
                self._load_errors[lookup_key] = str(exc)
                logger.warning("Failed to load plugin '%s': %s", lookup_key, exc)

        if manifests:
            logger.info(
                "Plugin discovery complete: %d found, %d enabled",
                len(self._plugins),
                sum(1 for p in self._plugins.values() if p.enabled),
            )

    # -----------------------------------------------------------------------
    # Directory scanning
    # -----------------------------------------------------------------------

    def _scan_directory(
        self,
        path: Path,
        source: str,
        skip_names: Optional[Set[str]] = None,
    ) -> List[PluginManifest]:
        """Read ``plugin.yaml`` manifests from subdirectories of *path*."""
        return self._scan_directory_level(
            path, source, skip_names=skip_names, prefix="", depth=0
        )

    def _scan_directory_level(
        self,
        path: Path,
        source: str,
        *,
        skip_names: Optional[Set[str]],
        prefix: str,
        depth: int,
    ) -> List[PluginManifest]:
        manifests: List[PluginManifest] = []
        if not path.is_dir():
            return manifests

        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            if depth == 0 and skip_names and child.name in skip_names:
                continue
            manifest_file = child / "plugin.yaml"
            if not manifest_file.exists():
                manifest_file = child / "plugin.yml"

            if manifest_file.exists():
                manifest = self._parse_manifest(
                    manifest_file, child, source, prefix
                )
                if manifest is not None:
                    manifests.append(manifest)
                continue

            if depth >= 1:
                logger.debug("Skipping %s (no plugin.yaml, depth cap reached)", child)
                continue

            sub_prefix = f"{prefix}/{child.name}" if prefix else child.name
            manifests.extend(
                self._scan_directory_level(
                    child,
                    source,
                    skip_names=None,
                    prefix=sub_prefix,
                    depth=depth + 1,
                )
            )

        return manifests

    def _parse_manifest(
        self,
        manifest_file: Path,
        plugin_dir: Path,
        source: str,
        prefix: str,
    ) -> Optional[PluginManifest]:
        """Parse a single ``plugin.yaml`` into a PluginManifest."""
        try:
            if yaml is None:
                logger.warning("PyYAML not installed – cannot load %s", manifest_file)
                return None
            data = _fast_safe_load(manifest_file.read_text(encoding="utf-8")) or {}

            name = data.get("name", plugin_dir.name)
            key = f"{prefix}/{plugin_dir.name}" if prefix else name

            raw_kind = data.get("kind", "standalone")
            if not isinstance(raw_kind, str):
                raw_kind = "standalone"
            kind = raw_kind.strip().lower()
            if kind not in _VALID_PLUGIN_KINDS:
                logger.warning(
                    "Plugin %s: unknown kind '%s' (valid: %s); treating as 'standalone'",
                    key, raw_kind, ", ".join(sorted(_VALID_PLUGIN_KINDS)),
                )
                kind = "standalone"

            if kind == "standalone" and "kind" not in data:
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    try:
                        source_text = init_file.read_text(errors="replace")[:8192]
                        if (
                            "register_memory_provider" in source_text
                            or "MemoryProvider" in source_text
                        ):
                            kind = "exclusive"
                            logger.debug(
                                "Plugin %s: detected memory provider, "
                                "treating as kind='exclusive'",
                                key,
                            )
                        elif (
                            "register_provider" in source_text
                            and "ProviderProfile" in source_text
                        ):
                            kind = "model-provider"
                            logger.debug(
                                "Plugin %s: detected model provider, "
                                "treating as kind='model-provider'",
                                key,
                            )
                    except Exception:
                        pass

            logger.debug(
                "Parsed manifest: key=%s name=%s kind=%s source=%s path=%s",
                key, name, kind, source, plugin_dir,
            )
            return PluginManifest(
                name=name,
                version=str(data.get("version", "")),
                description=data.get("description", ""),
                author=data.get("author", ""),
                requires_env=data.get("requires_env", []),
                provides_tools=data.get("provides_tools", []),
                provides_hooks=data.get("provides_hooks", []),
                source=source,
                path=str(plugin_dir),
                kind=kind,
                key=key,
            )
        except Exception as exc:
            logger.warning(
                "Failed to parse %s: %s", manifest_file, exc, exc_info=_PLUGINS_DEBUG,
            )
            return None

    # -----------------------------------------------------------------------
    # Entry-point scanning
    # -----------------------------------------------------------------------

    def _scan_entry_points(self) -> List[PluginManifest]:
        """Check ``importlib.metadata`` for pip-installed plugins."""
        manifests: List[PluginManifest] = []
        try:
            eps = importlib.metadata.entry_points()
            if hasattr(eps, "select"):
                group_eps = eps.select(group=ENTRY_POINTS_GROUP)
            elif isinstance(eps, dict):
                group_eps = eps.get(ENTRY_POINTS_GROUP, [])
            else:
                group_eps = [ep for ep in eps if ep.group == ENTRY_POINTS_GROUP]

            for ep in group_eps:
                manifest = PluginManifest(
                    name=ep.name,
                    source="entrypoint",
                    path=ep.value,
                    key=ep.name,
                )
                manifests.append(manifest)
        except Exception as exc:
            logger.debug("Entry-point scan failed: %s", exc)

        return manifests

    # -----------------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------------

    def _register_deferred_platform(self, manifest: PluginManifest) -> None:
        """Register a lazy loader for a bundled platform plugin."""
        lookup_key = manifest.key or manifest.name

        loaded = LoadedPlugin(manifest=manifest, enabled=True)
        loaded.deferred = True
        self._plugins[lookup_key] = loaded

        def _loader(_manifest: PluginManifest = manifest) -> None:
            self._load_plugin(_manifest)

        try:
            from gateway.platform_registry import platform_registry
            name = manifest.name or ""
            if name.endswith("-platform"):
                name = name[: -len("-platform")]
            elif manifest.path:
                name = Path(manifest.path).name
            platform_registry.register_deferred(name, _loader)
            logger.debug(
                "Registered deferred platform loader: %s (plugin=%s)",
                name,
                lookup_key,
            )
        except Exception:
            logger.debug(
                "Deferred platform registration failed for '%s'; eager-loading",
                lookup_key,
                exc_info=True,
            )
            self._load_plugin(manifest)

    def _load_plugin(self, manifest: PluginManifest) -> None:
        """Import a plugin module and call its ``register(ctx)`` function."""
        loaded = LoadedPlugin(manifest=manifest)
        logger.debug(
            "Loading plugin '%s' (source=%s, kind=%s, path=%s)",
            manifest.key or manifest.name, manifest.source, manifest.kind, manifest.path,
        )
        try:
            if manifest.source in {"user", "project", "bundled"}:
                module = self._load_directory_module(manifest)
            else:
                module = self._load_entrypoint_module(manifest)

            loaded.module = module

            register_fn = getattr(module, "register", None)
            if register_fn is None:
                loaded.error = "no register() function"
                logger.warning("Plugin '%s' has no register() function", manifest.name)
            else:
                ctx = PluginContext(manifest, self)
                _tools_before = set(self._plugin_tool_names)
                _hook_counts_before = {
                    h: len(cbs) for h, cbs in self._hooks.items()
                }
                _mw_counts_before = {
                    kind: len(cbs) for kind, cbs in self._middleware.items()
                }
                register_fn(ctx)
                loaded.tools_registered = [
                    t for t in self._plugin_tool_names
                    if t not in _tools_before
                ]
                loaded.hooks_registered = [
                    h
                    for h, cbs in self._hooks.items()
                    if len(cbs) > _hook_counts_before.get(h, 0)
                ]
                loaded.middleware_registered = [
                    kind
                    for kind, cbs in self._middleware.items()
                    if len(cbs) > _mw_counts_before.get(kind, 0)
                ]
                loaded.commands_registered = [
                    c for c in self._plugin_commands
                    if self._plugin_commands[c].get("plugin") == manifest.name
                ]
                loaded.enabled = True
                logger.debug(
                    "  registered: %d tool(s), %d hook(s), %d middleware, %d slash command(s), %d CLI command(s)",
                    len(loaded.tools_registered),
                    len(loaded.hooks_registered),
                    len(loaded.middleware_registered),
                    len(loaded.commands_registered),
                    sum(
                        1 for c in self._cli_commands
                        if self._cli_commands[c].get("plugin") == manifest.name
                    ),
                )

        except Exception as exc:
            loaded.error = str(exc)
            logger.warning(
                "Failed to load plugin '%s': %s",
                manifest.name, exc, exc_info=_PLUGINS_DEBUG,
            )
        self._plugins[manifest.key or manifest.name] = loaded

    def _load_directory_module(self, manifest: PluginManifest) -> types.ModuleType:
        """Import a directory-based plugin as ``agentz_plugins.<slug>``."""
        plugin_dir = Path(manifest.path)  # type: ignore[arg-type]
        init_file = plugin_dir / "__init__.py"
        if not init_file.exists():
            raise FileNotFoundError(f"No __init__.py in {plugin_dir}")

        if _NS_PARENT not in sys.modules:
            ns_pkg = types.ModuleType(_NS_PARENT)
            ns_pkg.__path__ = []  # type: ignore[attr-defined]
            ns_pkg.__package__ = _NS_PARENT
            sys.modules[_NS_PARENT] = ns_pkg

        key = manifest.key or manifest.name
        slug = key.replace("/", "__").replace("-", "_")
        module_name = f"{_NS_PARENT}.{slug}"
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_file,
            submodule_search_locations=[str(plugin_dir)],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {init_file}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = module_name
        module.__path__ = [str(plugin_dir)]  # type: ignore[attr-defined]
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _load_entrypoint_module(self, manifest: PluginManifest) -> types.ModuleType:
        """Load a pip-installed plugin via its entry-point reference."""
        eps = importlib.metadata.entry_points()
        if hasattr(eps, "select"):
            group_eps = eps.select(group=ENTRY_POINTS_GROUP)
        elif isinstance(eps, dict):
            group_eps = eps.get(ENTRY_POINTS_GROUP, [])
        else:
            group_eps = [ep for ep in eps if ep.group == ENTRY_POINTS_GROUP]

        for ep in group_eps:
            if ep.name == manifest.name:
                return ep.load()

        raise ImportError(
            f"Entry point '{manifest.name}' not found in group '{ENTRY_POINTS_GROUP}'"
        )

    # -----------------------------------------------------------------------
    # Hook invocation
    # -----------------------------------------------------------------------

    def invoke_hook(self, hook_name: str, **kwargs: Any) -> List[Any]:
        """Call all registered callbacks for *hook_name*."""
        callbacks = self._hooks.get(hook_name, [])
        results: List[Any] = []
        for cb in callbacks:
            try:
                ret = cb(**kwargs)
                if ret is not None:
                    results.append(ret)
            except Exception as exc:
                logger.warning(
                    "Hook '%s' callback %s raised: %s",
                    hook_name,
                    getattr(cb, "__name__", repr(cb)),
                    exc,
                )
        return results

    def has_hook(self, hook_name: str) -> bool:
        """Return True when at least one callback is registered for a hook."""
        return bool(self._hooks.get(hook_name))

    def has_middleware(self, kind: str) -> bool:
        return bool(self._middleware.get(kind))

    def invoke_middleware(self, kind: str, **kwargs: Any) -> List[Any]:
        callbacks = self._middleware.get(kind, [])
        results: List[Any] = []
        for cb in callbacks:
            try:
                ret = cb(**kwargs)
                if ret is not None:
                    results.append(ret)
            except Exception as exc:
                logger.warning(
                    "Middleware '%s' callback %s raised: %s",
                    kind,
                    getattr(cb, "__name__", repr(cb)),
                    exc,
                )
        return results

    # -----------------------------------------------------------------------
    # Introspection
    # -----------------------------------------------------------------------

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Return a list of info dicts for all discovered plugins."""
        result: List[Dict[str, Any]] = []
        for key, loaded in sorted(self._plugins.items()):
            result.append(
                {
                    "name": loaded.manifest.name,
                    "key": loaded.manifest.key or loaded.manifest.name,
                    "kind": loaded.manifest.kind,
                    "version": loaded.manifest.version,
                    "description": loaded.manifest.description,
                    "source": loaded.manifest.source,
                    "enabled": loaded.enabled,
                    "tools": len(loaded.tools_registered),
                    "hooks": len(loaded.hooks_registered),
                    "middleware": len(loaded.middleware_registered),
                    "commands": len(loaded.commands_registered),
                    "error": loaded.error,
                }
            )
        return result

    # -- Introspection: manifest listing / lookup --------------------------

    @property
    def loaded_plugins(self) -> Dict[str, "LoadedPlugin"]:
        """Return the map of loaded plugins (name → LoadedPlugin)."""
        return self._plugins

    @property
    def load_errors(self) -> Dict[str, str]:
        """Return a map of plugin name → error message for plugins that failed to load."""
        return self._load_errors

    def list_manifests(
        self,
        *,
        include_disabled: bool = True,
        source: Optional[str] = None,
    ) -> List["PluginManifest"]:
        """Return manifest objects for all known plugins.

        Args:
            include_disabled: If True, include plugins disabled via config.
            source:         If set, only include manifests from one source
                            (``bundled`` | ``user`` | ``project`` | ``entrypoint``).
        """
        disabled = _get_disabled_plugins() if not include_disabled else set()

        collected: Dict[str, PluginManifest] = {}
        for key, mf in self._manifests.items():
            if source and mf.source != source:
                continue
            if not include_disabled and (mf.name in disabled or key in disabled):
                continue
            collected[mf.name or key] = mf

        # Also surface manifests that are only known via LoadedPlugin entries
        for key, entry in self._plugins.items():
            mf = entry.manifest
            if not mf or not (mf.name or key):
                continue
            if source and mf.source != source:
                continue
            if not include_disabled and (mf.name in disabled or key in disabled):
                continue
            collected.setdefault(mf.name or key, mf)

        return sorted(collected.values(), key=lambda m: (m.source or "", m.name or ""))

    def get_manifest(self, plugin_name: str) -> Optional["PluginManifest"]:
        """Return the manifest for a plugin by name or key, or ``None``."""
        if not plugin_name:
            return None
        mf = self._manifests.get(plugin_name)
        if mf is not None:
            return mf
        entry = self._plugins.get(plugin_name)
        if entry is not None:
            return entry.manifest
        for _key, entry in self._plugins.items():
            if entry.manifest and entry.manifest.name == plugin_name:
                return entry.manifest
        return None

    def is_plugin_disabled(self, plugin_name: str) -> bool:
        """Return True if the plugin is explicitly disabled in the user config."""
        if not plugin_name:
            return False
        disabled = _get_disabled_plugins()
        if plugin_name in disabled:
            return True
        entry = self._plugins.get(plugin_name)
        if entry is not None and not entry.enabled:
            # Some plugins are "disabled" by the loader (exclusive, manifest-only, etc)
            # but that's semantic — only report true if config disabled it
            disabled_reasons = ("disabled via config", "not enabled in config")
            if entry.error and any(s in entry.error for s in disabled_reasons):
                return True
            if entry.manifest and entry.manifest.key and entry.manifest.key in disabled:
                return True
        return False

    def find_plugin_skill(self, qualified_name: str) -> Optional[Path]:
        entry = self._plugin_skills.get(qualified_name)
        return entry["path"] if entry else None

    def list_plugin_skills(self, plugin_name: str) -> List[str]:
        prefix = f"{plugin_name}:"
        return sorted(
            e["bare_name"]
            for qn, e in self._plugin_skills.items()
            if qn.startswith(prefix)
        )

    def get_memory_providers(self) -> Dict[str, Any]:
        return dict(self._memory_providers)

    def get_context_engines(self) -> Dict[str, Any]:
        return dict(self._context_engines)

    def get_model_providers(self) -> Dict[str, Any]:
        return dict(self._model_providers)

    def get_web_search_backends(self) -> Dict[str, Any]:
        return dict(self._web_search_backends)

    def get_tool_providers(self) -> Dict[str, Any]:
        return dict(self._tool_providers)

    def get_plugin_context_engine(self) -> Any:
        return self._context_engine

    def get_auxiliary_tasks(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._aux_tasks)

    def get_cli_commands(self) -> Dict[str, dict]:
        return dict(self._cli_commands)

    def get_slash_commands(self) -> Dict[str, dict]:
        return dict(self._plugin_commands)


# ---------------------------------------------------------------------------
# Module-level singleton & convenience functions
# ---------------------------------------------------------------------------

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Return (and lazily create) the global PluginManager singleton."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def discover_plugins(force: bool = False) -> None:
    """Discover and load all plugins."""
    get_plugin_manager().discover_and_load(force=force)


def invoke_hook(hook_name: str, **kwargs: Any) -> List[Any]:
    """Invoke a lifecycle hook on all loaded plugins."""
    return get_plugin_manager().invoke_hook(hook_name, **kwargs)


def invoke_middleware(kind: str, **kwargs: Any) -> List[Any]:
    """Invoke registered middleware callbacks."""
    return get_plugin_manager().invoke_middleware(kind, **kwargs)


def has_middleware(kind: str) -> bool:
    manager = get_plugin_manager()
    method = getattr(manager, "has_middleware", None)
    if callable(method):
        return bool(method(kind))
    return bool(getattr(manager, "_middleware", {}).get(kind))


def has_hook(hook_name: str) -> bool:
    return get_plugin_manager().has_hook(hook_name)


def list_plugins() -> List[Dict[str, Any]]:
    """Return all discovered plugins as a list of info dicts."""
    discover_plugins()
    return get_plugin_manager().list_plugins()


def get_memory_providers() -> Dict[str, Any]:
    discover_plugins()
    return get_plugin_manager().get_memory_providers()


def get_plugin_context_engine() -> Any:
    discover_plugins()
    return get_plugin_manager().get_plugin_context_engine()


def find_plugin_skill(qualified_name: str) -> Optional[Path]:
    discover_plugins()
    return get_plugin_manager().find_plugin_skill(qualified_name)


def set_plugin_cli_ref(cli: Any) -> None:
    """Attach a CLI reference so plugins can inject_message and dispatch_tool."""
    get_plugin_manager().set_cli_ref(cli)
