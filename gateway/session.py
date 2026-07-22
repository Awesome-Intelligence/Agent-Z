# 🚪 Access - gateway/session.py
"""
Session management for the gateway.
Ported from Hermes agent - https://github.com/NousResearch/hermes-agent

Provides:
- Platform / SessionSource / SessionEntry data classes
- Session key building (build_session_key)
- GatewaySessionStore: routes messages to agent/state/session_store.py (SQLite)
  and manages the session_key → session_id routing index (sessions.json)
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_logger

logger = get_logger("gateway.session")


def _now() -> datetime:
    return datetime.now()


def _hash_id(value: str) -> str:
    """Deterministic 12-char hex hash of an identifier."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _hash_sender_id(value: str) -> str:
    """Hash a sender ID to ``user_<12hex>``."""
    return f"user_{_hash_id(value)}"


def _hash_chat_id(value: str) -> str:
    """Hash the numeric portion of a chat ID, preserving platform prefix."""
    colon = value.find(":")
    if colon > 0:
        prefix = value[:colon]
        return f"{prefix}:{_hash_id(value[colon + 1:])}"
    return _hash_id(value)


class Platform(Enum):
    """Supported messaging platforms."""

    LOCAL = "local"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    WHATSAPP_CLOUD = "whatsapp_cloud"
    SLACK = "slack"
    SIGNAL = "signal"
    MATTERMOST = "mattermost"
    MATRIX = "matrix"
    HOMEASSISTANT = "homeassistant"
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    API_SERVER = "api_server"
    WEBHOOK = "webhook"
    MSGRAPH_WEBHOOK = "msgraph_webhook"
    FEISHU = "feishu"
    WECOM = "wecom"
    WECOM_CALLBACK = "wecom_callback"
    WEIXIN = "weixin"
    BLUEBUBBLES = "bluebubbles"
    QQBOT = "qqbot"
    YUANBAO = "yuanbao"
    RELAY = "relay"
    NTFY = "ntfy"
    GOOGLE_CHAT = "google_chat"
    PHOTON = "photon"
    LINE = "line"
    IRC = "irc"
    TEAMS = "teams"
    RAFT = "raft"
    SIMPLEX = "simplex"

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str) or not value.strip():
            return None
        value = value.strip().lower()
        if value in cls._value2member_map_:
            return cls._value2member_map_[value]
        return None


@dataclass
class SessionSource:
    """Describes where a message originated from."""

    platform: Platform
    chat_id: str
    chat_name: str | None = None
    chat_type: str = "dm"
    user_id: str | None = None
    user_name: str | None = None
    thread_id: str | None = None
    chat_topic: str | None = None
    user_id_alt: str | None = None
    chat_id_alt: str | None = None
    is_bot: bool = False
    scope_id: str | None = None
    guild_id: str | None = None
    parent_chat_id: str | None = None
    message_id: str | None = None
    role_authorized: bool = False
    profile: str | None = None
    delivered_via_upstream_relay: bool = False

    def __post_init__(self) -> None:
        if self.scope_id is None and self.guild_id is not None:
            self.scope_id = self.guild_id
        elif self.scope_id is not None:
            self.guild_id = self.scope_id

    @property
    def description(self) -> str:
        """Human-readable description of the source."""
        if self.platform == Platform.LOCAL:
            return "CLI terminal"

        parts = []
        if self.chat_type == "dm":
            parts.append(f"DM with {self.user_name or self.user_id or 'user'}")
        elif self.chat_type == "group":
            parts.append(f"group: {self.chat_name or self.chat_id}")
        elif self.chat_type == "channel":
            parts.append(f"channel: {self.chat_name or self.chat_id}")
        else:
            parts.append(self.chat_name or self.chat_id)

        if self.thread_id:
            parts.append(f"thread: {self.thread_id}")

        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "chat_id": self.chat_id,
            "chat_name": self.chat_name,
            "chat_type": self.chat_type,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "thread_id": self.thread_id,
            "chat_topic": self.chat_topic,
            "user_id_alt": self.user_id_alt,
            "chat_id_alt": self.chat_id_alt,
            "is_bot": self.is_bot,
            "scope_id": self.scope_id,
            "guild_id": self.guild_id,
            "parent_chat_id": self.parent_chat_id,
            "message_id": self.message_id,
            "role_authorized": self.role_authorized,
            "profile": self.profile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionSource":
        return cls(
            platform=Platform(data["platform"]),
            chat_id=str(data["chat_id"]),
            chat_name=data.get("chat_name"),
            chat_type=data.get("chat_type", "dm"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
            thread_id=data.get("thread_id"),
            chat_topic=data.get("chat_topic"),
            user_id_alt=data.get("user_id_alt"),
            chat_id_alt=data.get("chat_id_alt"),
            is_bot=data.get("is_bot", False),
            scope_id=data.get("scope_id", data.get("guild_id")),
            parent_chat_id=data.get("parent_chat_id"),
            message_id=data.get("message_id"),
            role_authorized=data.get("role_authorized", False),
            profile=data.get("profile"),
        )


def _session_key_namespace(profile: Optional[str]) -> str:
    if not profile or profile == "default":
        return "agent:main"
    return f"agent:{profile}"


def build_session_key(
    source: SessionSource,
    group_sessions_per_user: bool = True,
    thread_sessions_per_user: bool = False,
    profile: Optional[str] = None,
) -> str:
    """Build a deterministic session key from a message source."""
    ns = _session_key_namespace(profile)
    platform = source.platform.value

    if source.chat_type == "dm":
        dm_chat_id = source.chat_id
        if dm_chat_id:
            if source.thread_id:
                return f"{ns}:{platform}:dm:{dm_chat_id}:{source.thread_id}"
            return f"{ns}:{platform}:dm:{dm_chat_id}"

        dm_participant_id = source.user_id_alt or source.user_id
        if dm_participant_id:
            if source.thread_id:
                return f"{ns}:{platform}:dm:{dm_participant_id}:{source.thread_id}"
            return f"{ns}:{platform}:dm:{dm_participant_id}"
        if source.thread_id:
            return f"{ns}:{platform}:dm:{source.thread_id}"
        return f"{ns}:{platform}:dm"

    participant_id = source.user_id_alt or source.user_id
    key_parts = [ns, platform, source.chat_type]

    if source.chat_id:
        key_parts.append(source.chat_id)
    if source.thread_id:
        key_parts.append(source.thread_id)

    isolate_user = group_sessions_per_user
    if source.thread_id and not thread_sessions_per_user:
        isolate_user = False

    if isolate_user and participant_id:
        key_parts.append(str(participant_id))

    return ":".join(key_parts)


# ── Path safety ──────────────────────────────────────────────────────────────

def _is_path_unsafe(value: object) -> bool:
    """Reject session keys/ids that could traverse outside the sessions dir."""
    if not value:
        return False
    s = str(value)
    if ".." in s or "/" in s or "\\" in s:
        return True
    return len(s) >= 2 and s[0].isalpha() and s[1] == ":"


# ── Model override sanitization ──────────────────────────────────────────────

PERSISTABLE_MODEL_OVERRIDE_KEYS = ("model", "provider", "base_url")


def sanitize_model_override(override: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Return a copy of *override* containing only persistable, non-secret keys."""
    if not isinstance(override, dict):
        return None
    cleaned = {
        k: str(v)
        for k, v in override.items()
        if k in PERSISTABLE_MODEL_OVERRIDE_KEYS and v not in (None, "")
    }
    return cleaned or None


# ── SessionEntry ──────────────────────────────────────────────────────────────


@dataclass
class SessionEntry:
    """Entry in the gateway's session routing index."""

    session_key: str
    session_id: str
    created_at: datetime
    updated_at: datetime

    # Origin metadata
    origin: Optional[SessionSource] = None

    # Display metadata
    display_name: Optional[str] = None
    platform: Optional[Platform] = None
    chat_type: str = "dm"

    # Token tracking
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Session state flags
    was_auto_reset: bool = False
    auto_reset_reason: Optional[str] = None
    is_fresh_reset: bool = False
    suspended: bool = False
    resume_pending: bool = False
    resume_reason: Optional[str] = None
    last_resume_marked_at: Optional[datetime] = None

    # Session-scoped model override (never credentials)
    model_override: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "session_key": self.session_key,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "display_name": self.display_name,
            "platform": self.platform.value if self.platform else None,
            "chat_type": self.chat_type,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "was_auto_reset": self.was_auto_reset,
            "auto_reset_reason": self.auto_reset_reason,
            "is_fresh_reset": self.is_fresh_reset,
            "suspended": self.suspended,
            "resume_pending": self.resume_pending,
            "resume_reason": self.resume_reason,
            "last_resume_marked_at": (
                self.last_resume_marked_at.isoformat() if self.last_resume_marked_at else None
            ),
        }
        if self.model_override:
            result["model_override"] = sanitize_model_override(self.model_override)
        if self.origin:
            result["origin"] = self.origin.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionEntry":
        origin = None
        if "origin" in data and isinstance(data["origin"], dict):
            origin = SessionSource.from_dict(data["origin"])

        platform = None
        if data.get("platform"):
            try:
                platform = Platform(data["platform"])
            except ValueError as e:
                logger.debug("Unknown platform value %r: %s", data["platform"], e)

        last_resume_marked_at = None
        _lrma = data.get("last_resume_marked_at")
        if _lrma:
            try:
                last_resume_marked_at = datetime.fromisoformat(_lrma)
            except (TypeError, ValueError):
                last_resume_marked_at = None

        session_key = data["session_key"]
        session_id = data["session_id"]

        for _field, _val in (("session_key", session_key), ("session_id", session_id)):
            if _is_path_unsafe(_val):
                raise ValueError(f"Invalid {_field}: potential directory traversal detected")

        return cls(
            session_key=session_key,
            session_id=session_id,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            origin=origin,
            display_name=data.get("display_name"),
            platform=platform,
            chat_type=data.get("chat_type", "dm"),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
            was_auto_reset=data.get("was_auto_reset", False),
            auto_reset_reason=data.get("auto_reset_reason"),
            is_fresh_reset=data.get("is_fresh_reset", False),
            suspended=data.get("suspended", False),
            resume_pending=data.get("resume_pending", False),
            resume_reason=data.get("resume_reason"),
            last_resume_marked_at=last_resume_marked_at,
            model_override=sanitize_model_override(data.get("model_override")),
        )


# ── GatewaySessionStore ───────────────────────────────────────────────────────
# Bridges the gateway's session_key → session_id routing index (sessions.json)
# with the agent's SQLite message store (agent/state/session_store.py).


class GatewaySessionStore:
    """
    Manages session routing and delegates message persistence to the agent's
    SQLite SessionStore (agent/state/session_store.py).

    This class provides the same interface that the gateway runner expects:
    - get_or_create_session(source) → SessionEntry
    - reset_session(session_key, display_name) → SessionEntry
    - set_model_override(session_key, override) → None
    - get_model_override(session_key) → Optional[Dict]
    - append_to_transcript(session_id, message) → None
    - load_transcript(session_id) → List[Dict]
    """

    def __init__(
        self,
        sessions_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._sessions_dir = Path(sessions_dir) if sessions_dir else self._default_sessions_dir()
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._config = config or {}

        self._entries: Dict[str, SessionEntry] = {}
        self._loaded = False
        self._lock = threading.Lock()

        # Delegate message persistence to the agent's SQLite store
        self._db: Any = None
        try:
            from agent.state.session_store import SessionStore as AgentSessionStore
            self._db = AgentSessionStore()
        except Exception as e:
            logger.warning("SQLite session store unavailable, falling back to memory-only: %s", e)

    @staticmethod
    def _default_sessions_dir() -> Path:
        try:
            from gateway.platforms._hermes_stubs import get_hermes_home
            return Path(get_hermes_home()) / "gateway_sessions"
        except Exception:
            return Path.home() / ".agent_z" / "gateway_sessions"

    # ── sessions.json I/O ────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        with self._lock:
            self._ensure_loaded_locked()

    def _ensure_loaded_locked(self) -> None:
        if self._loaded:
            return
        sessions_file = self._sessions_dir / "sessions.json"
        if sessions_file.exists():
            try:
                with open(sessions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, entry_data in data.items():
                    if key.startswith("_") or not isinstance(entry_data, dict):
                        continue
                    try:
                        self._entries[key] = SessionEntry.from_dict(entry_data)
                    except (ValueError, KeyError, TypeError) as e:
                        logger.warning("Skipping invalid session entry %r: %s", key, e)
            except Exception as e:
                logger.warning("Failed to load sessions: %s", e)
        self._loaded = True

    def _save(self) -> None:
        data = {key: entry.to_dict() for key, entry in self._entries.items()}
        data = {
            "_README": (
                "Gateway routing index ONLY: maps messaging session keys "
                "(agent:main:<platform>:...) to active session IDs. "
                "Message history lives in the SQLite session store."
            ),
            **data,
        }
        sessions_file = self._sessions_dir / "sessions.json"
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._sessions_dir), suffix=".tmp", prefix=".sessions_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # atomic_replace equivalent on Windows
            bak = str(sessions_file) + ".bak"
            if sessions_file.exists():
                try:
                    os.replace(str(sessions_file), bak)
                except OSError:
                    pass
            os.replace(tmp_path, str(sessions_file))
            try:
                os.unlink(bak)
            except OSError:
                pass
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ── Session management ───────────────────────────────────────────────────

    def get_or_create_session(
        self,
        source: SessionSource,
        force_new: bool = False,
    ) -> SessionEntry:
        """Get existing session or create a new one for the source."""
        session_key = build_session_key(source)
        now = _now()

        with self._lock:
            self._ensure_loaded_locked()

            if session_key in self._entries and not force_new:
                entry = self._entries[session_key]
                entry.updated_at = now
                self._save()
                return entry

            # Create new session
            session_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            entry = SessionEntry(
                session_key=session_key,
                session_id=session_id,
                created_at=now,
                updated_at=now,
                origin=source,
                display_name=source.chat_name,
                platform=source.platform,
                chat_type=source.chat_type,
            )
            self._entries[session_key] = entry
            self._save()

        # Create SQLite row outside the lock
        if self._db:
            try:
                self._db.create_session(
                    session_id=session_id,
                    source=source.platform.value,
                    user_id=source.user_id,
                )
            except Exception as e:
                logger.debug("SQLite create_session failed: %s", e)

        return entry

    def reset_session(
        self,
        session_key: str,
        display_name: Optional[str] = None,
    ) -> Optional[SessionEntry]:
        """Force-reset a session, creating a new session_id."""
        with self._lock:
            self._ensure_loaded_locked()

            if session_key not in self._entries:
                return None

            old_entry = self._entries[session_key]
            old_session_id = old_entry.session_id

            now = _now()
            session_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            new_entry = SessionEntry(
                session_key=session_key,
                session_id=session_id,
                created_at=now,
                updated_at=now,
                origin=old_entry.origin,
                display_name=display_name if display_name is not None else old_entry.display_name,
                platform=old_entry.platform,
                chat_type=old_entry.chat_type,
                is_fresh_reset=True,
            )
            self._entries[session_key] = new_entry
            self._save()

        # End old session, create new one in SQLite
        if self._db:
            try:
                self._db.end_session(old_session_id, "session_reset")
            except Exception as e:
                logger.debug("SQLite end_session failed: %s", e)
            try:
                source_platform = old_entry.platform.value if old_entry.platform else "unknown"
                self._db.create_session(
                    session_id=session_id,
                    source=source_platform,
                    user_id=old_entry.origin.user_id if old_entry.origin else None,
                )
            except Exception as e:
                logger.debug("SQLite create_session failed: %s", e)

        return new_entry

    def set_model_override(
        self, session_key: str, override: Optional[Dict[str, Any]]
    ) -> None:
        """Persist (or clear) the session-scoped model override."""
        with self._lock:
            self._ensure_loaded_locked()
            entry = self._entries.get(session_key)
            if entry is None:
                return
            cleaned = sanitize_model_override(override)
            if entry.model_override == cleaned:
                return
            entry.model_override = cleaned
            self._save()

    def get_model_override(self, session_key: str) -> Optional[Dict[str, str]]:
        """Return the persisted model override for *session_key*, if any."""
        with self._lock:
            self._ensure_loaded_locked()
            entry = self._entries.get(session_key)
            if entry is None:
                return None
            return dict(entry.model_override) if entry.model_override else None

    def suspend_session(self, session_key: str) -> bool:
        """Mark a session as suspended so it auto-resets on next access."""
        with self._lock:
            self._ensure_loaded_locked()
            if session_key in self._entries:
                self._entries[session_key].suspended = True
                self._save()
                return True
        return False

    # ── Transcript (SQLite) ──────────────────────────────────────────────────

    def append_to_transcript(
        self, session_id: str, message: Dict[str, Any], skip_db: bool = False
    ) -> None:
        """Append a message to a session's transcript."""
        if self._db and not skip_db:
            try:
                self._db.add_message(
                    session_id=session_id,
                    role=message.get("role", "unknown"),
                    content=message.get("content"),
                    tool_call_id=message.get("tool_call_id"),
                    tool_calls=message.get("tool_calls"),
                    tool_name=message.get("tool_name"),
                    reasoning=message.get("reasoning"),
                )
            except Exception as e:
                logger.debug("append_to_transcript failed: %s", e)

    def load_transcript(self, session_id: str) -> List[Dict[str, Any]]:
        """Load all messages from a session's transcript."""
        if not self._db:
            return []
        try:
            return self._db.get_messages(session_id)
        except Exception as e:
            logger.debug("load_transcript failed: %s", e)
            return []

    def list_sessions(self, active_minutes: Optional[int] = None) -> List[SessionEntry]:
        """List all sessions, optionally filtered by recent activity."""
        with self._lock:
            self._ensure_loaded_locked()
            entries = list(self._entries.values())

        if active_minutes is not None:
            cutoff = _now() - timedelta(minutes=active_minutes)
            entries = [e for e in entries if e.updated_at >= cutoff]

        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries

    def close(self) -> None:
        """Close the SQLite connection."""
        if self._db:
            try:
                self._db.close()
            except Exception:
                pass
