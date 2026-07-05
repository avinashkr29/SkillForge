from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Tuple

from app.models import SessionState


ALLOWED_TRANSITIONS = {
    SessionState.IDLE: {SessionState.LISTENING, SessionState.PARSING_COMMAND, SessionState.SEARCHING, SessionState.STOPPED, SessionState.ERROR},
    SessionState.LISTENING: {SessionState.PARSING_COMMAND, SessionState.IDLE, SessionState.ERROR},
    SessionState.PARSING_COMMAND: {SessionState.SEARCHING, SessionState.STOPPED, SessionState.ERROR, SessionState.IDLE},
    SessionState.SEARCHING: {SessionState.PARSING_COMMAND, SessionState.NEEDS_SELECTION, SessionState.LOCKED, SessionState.ERROR, SessionState.STOPPED, SessionState.IDLE},
    SessionState.NEEDS_SELECTION: {SessionState.LOCKED, SessionState.SEARCHING, SessionState.PARSING_COMMAND, SessionState.STOPPED, SessionState.ERROR},
    SessionState.LOCKED: {SessionState.TRACKING, SessionState.PARSING_COMMAND, SessionState.TEMPORARILY_LOST, SessionState.STOPPED, SessionState.ERROR},
    SessionState.TRACKING: {SessionState.PARSING_COMMAND, SessionState.TEMPORARILY_LOST, SessionState.LOST, SessionState.STOPPED, SessionState.ERROR},
    SessionState.TEMPORARILY_LOST: {SessionState.PARSING_COMMAND, SessionState.TRACKING, SessionState.LOST, SessionState.STOPPED, SessionState.ERROR},
    SessionState.LOST: {SessionState.SEARCHING, SessionState.PARSING_COMMAND, SessionState.STOPPED, SessionState.ERROR},
    SessionState.STOPPED: {SessionState.IDLE, SessionState.PARSING_COMMAND, SessionState.SEARCHING, SessionState.ERROR},
    SessionState.ERROR: {
        SessionState.IDLE,
        SessionState.PARSING_COMMAND,
        SessionState.SEARCHING,
        SessionState.NEEDS_SELECTION,
        SessionState.LOCKED,
        SessionState.TRACKING,
        SessionState.TEMPORARILY_LOST,
        SessionState.LOST,
        SessionState.STOPPED,
    },
}


@dataclass
class TransitionLogEntry:
    previous: SessionState
    current: SessionState
    reason: str
    ts: datetime


@dataclass
class TrackingSessionController:
    state: SessionState = SessionState.IDLE
    transitions: List[TransitionLogEntry] = field(default_factory=list)

    def transition_to(self, next_state: SessionState, reason: str) -> TransitionLogEntry:
        if next_state == self.state:
            entry = TransitionLogEntry(self.state, next_state, reason, datetime.now(timezone.utc))
            self.transitions.append(entry)
            return entry
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if next_state not in allowed:
            raise ValueError(f"Invalid session transition {self.state.value} -> {next_state.value}")
        entry = TransitionLogEntry(self.state, next_state, reason, datetime.now(timezone.utc))
        self.state = next_state
        self.transitions.append(entry)
        return entry

    def latest_transition(self) -> Tuple[str, str]:
        if not self.transitions:
            return (self.state.value, "initial")
        entry = self.transitions[-1]
        return (f"{entry.previous.value} -> {entry.current.value}", entry.reason)
