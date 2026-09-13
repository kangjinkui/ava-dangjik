"""Serialization helpers for the read-only live transcript feed."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


MAX_MESSAGES_PER_CALL = 500
MAX_TOOL_EVENTS_PER_CALL = 500
_TOOL_EVENT_PHASES = {"started", "completed"}
_TOOL_EVENT_STATUSES = {
    "running", "success", "failure", "timeout", "cancelled", "unknown"
}


def _iso_timestamp(value: Any, fallback: float) -> str:
    """Return an ISO-8601 UTC timestamp for supported session/history values."""
    if isinstance(value, datetime):
        timestamp = value
    else:
        try:
            timestamp = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            if isinstance(value, str):
                try:
                    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.fromtimestamp(fallback, tz=timezone.utc)
            else:
                timestamp = datetime.fromtimestamp(fallback, tz=timezone.utc)

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_safe(value: Any) -> Any:
    """Return a bounded JSON-safe copy of already-redacted event data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in list(value.items())[:100]}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in list(value)[:100]]
    return str(value)


def _tool_event_snapshot(session: Any, *, active: bool, fallback: float) -> list[dict[str, Any]]:
    raw_events = list(getattr(session, "tool_events", None) or [])[-MAX_TOOL_EVENTS_PER_CALL:]
    completed_ids = {
        str(event.get("id") or "")
        for event in raw_events
        if isinstance(event, dict) and event.get("phase") == "completed"
    }
    events: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        phase = str(event.get("phase") or "")
        if phase not in _TOOL_EVENT_PHASES:
            continue
        event_id = str(event.get("id") or "").strip()
        tool_call_id = str(event.get("tool_call_id") or "").strip()
        if not event_id or not tool_call_id:
            continue
        status = str(event.get("status") or "unknown").strip().lower()
        if status not in _TOOL_EVENT_STATUSES:
            status = "unknown"
        # An invocation that outlives its call is no longer known to be running.
        if not active and phase == "started" and event_id not in completed_ids:
            status = "unknown"
        item: dict[str, Any] = {
            "id": event_id,
            "tool_call_id": tool_call_id,
            "name": str(event.get("name") or "unknown"),
            "phase": phase,
            "status": status,
            "created_at": _iso_timestamp(event.get("created_at"), fallback),
        }
        if "duration_ms" in event:
            try:
                item["duration_ms"] = round(max(0.0, float(event["duration_ms"])), 2)
            except (TypeError, ValueError):
                pass
        for key in ("params", "message", "result"):
            if key in event:
                item[key] = _json_safe(event[key])
        events.append(item)
    return events


def transcript_snapshot(session: Any, *, active: bool) -> dict[str, Any]:
    """Build a bounded JSON-safe transcript snapshot from a call session."""
    try:
        started_epoch = float(getattr(session, "created_at", 0.0) or 0.0)
    except (TypeError, ValueError):
        started_epoch = 0.0

    history = list(getattr(session, "conversation_history", None) or [])
    messages = []
    for index, entry in enumerate(history):
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = entry.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        messages.append(
            {
                "id": str(index),
                "role": role,
                "text": content,
                "created_at": _iso_timestamp(entry.get("timestamp"), started_epoch),
            }
        )

    return {
        "call_id": str(getattr(session, "call_id", "")),
        "started_at": _iso_timestamp(started_epoch, 0.0),
        "status": str(getattr(session, "status", "unknown") or "unknown"),
        "active": active,
        "messages": messages[-MAX_MESSAGES_PER_CALL:],
        "tool_events": _tool_event_snapshot(session, active=active, fallback=started_epoch),
    }
