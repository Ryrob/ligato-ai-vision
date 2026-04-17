"""In-memory session store that links voice calls to MMS by phone number.

For a real deployment, swap this for Redis or a database. The key property the prototype
needs is: given an inbound MMS from phone X, look up the active call session for X.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallSession:
    call_sid: str
    caller: str  # E.164 phone number, e.g. "+15551230001"
    started_at: float = field(default_factory=time.time)
    # Running Claude message history for the voice agent.
    messages: list[dict[str, Any]] = field(default_factory=list)
    # Queue of vision results waiting to be handed to the next voice turn.
    pending_vision: asyncio.Queue = field(default_factory=asyncio.Queue)
    # The tool_use_id for the most recent outstanding request_media_from_caller call.
    awaiting_tool_id: str | None = None
    # Simple event log (for the dashboard / debugging).
    events: list[dict[str, Any]] = field(default_factory=list)

    def log(self, channel: str, kind: str, **fields):
        self.events.append({"ts": time.time(), "channel": channel, "kind": kind, **fields})


class SessionStore:
    def __init__(self) -> None:
        self._by_sid: dict[str, CallSession] = {}
        self._by_caller: dict[str, CallSession] = {}

    def start(self, call_sid: str, caller: str) -> CallSession:
        session = CallSession(call_sid=call_sid, caller=caller)
        self._by_sid[call_sid] = session
        self._by_caller[caller] = session
        return session

    def get(self, call_sid: str) -> CallSession | None:
        return self._by_sid.get(call_sid)

    def get_by_caller(self, caller: str) -> CallSession | None:
        return self._by_caller.get(caller)

    def end(self, call_sid: str) -> None:
        session = self._by_sid.pop(call_sid, None)
        if session:
            self._by_caller.pop(session.caller, None)


store = SessionStore()
