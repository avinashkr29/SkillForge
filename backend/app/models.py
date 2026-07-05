from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Intent(str, Enum):
    TRACK_OBJECT = "track_object"
    STOP_TRACKING = "stop_tracking"
    UNCLEAR = "unclear"


class SessionState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PARSING_COMMAND = "PARSING_COMMAND"
    SEARCHING = "SEARCHING"
    NEEDS_SELECTION = "NEEDS_SELECTION"
    LOCKED = "LOCKED"
    TRACKING = "TRACKING"
    TEMPORARILY_LOST = "TEMPORARILY_LOST"
    LOST = "LOST"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class TargetStatus(str, Enum):
    SEARCHING = "SEARCHING"
    LOCKED = "LOCKED"
    TRACKING = "TRACKING"
    TEMPORARILY_LOST = "TEMPORARILY_LOST"
    LOST = "LOST"


class ResolverStatus(str, Enum):
    AUTO_LOCKED = "AUTO_LOCKED"
    NEEDS_SELECTION = "NEEDS_SELECTION"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"


class ObjectAttributes(BaseModel):
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    position: Optional[str] = None


class ParsedCommand(BaseModel):
    intent: Intent
    object_phrase: Optional[str] = None
    base_object: Optional[str] = None
    attributes: ObjectAttributes = Field(default_factory=ObjectAttributes)
    action_context: Optional[str] = None
    requires_confirmation: bool = False
    reason: str = ""

    @field_validator("object_phrase", "base_object")
    @classmethod
    def normalize_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = " ".join(value.strip().lower().split())
        return value or None


class TranscriptResult(BaseModel):
    transcript: str
    is_final: bool = True
    confidence: Optional[float] = None


class DetectionResult(BaseModel):
    detection_id: str
    label: str
    confidence: float
    bbox: List[float]
    mask: Optional[Any] = None
    prompt_version: int

    @field_validator("bbox")
    @classmethod
    def bbox_has_four_values(cls, value: List[float]) -> List[float]:
        if len(value) != 4:
            raise ValueError("bbox must contain [x1, y1, x2, y2]")
        return value


class CandidateResolution(BaseModel):
    status: ResolverStatus
    selected_detection_id: Optional[str] = None
    candidates: List[DetectionResult] = Field(default_factory=list)


class TargetState(BaseModel):
    target_id: str
    tracker_id: int
    label: str
    bbox: List[float]
    confidence: float
    status: TargetStatus
    last_seen_ts: datetime
    lost_frames: int = 0


class Metrics(BaseModel):
    video_fps: float = 0
    yoloe_inference_latency_ms: float = 0
    context_verification_latency_ms: float = 0
    speech_transcription_latency_ms: float = 0
    command_parsing_latency_ms: float = 0
    transcript_to_first_detection_ms: float = 0
    tracking_update_latency_ms: float = 0
    id_switches: int = 0
    lost_and_reacquired_count: int = 0


class WebSocketEnvelope(BaseModel):
    type: str
    ts: datetime = Field(default_factory=utc_now)
    frame_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class TypedCommandRequest(BaseModel):
    text: str


class CandidateSelectionRequest(BaseModel):
    x: float
    y: float
    display_width: float
    display_height: float
    frame_width: float
    frame_height: float


class FramePayload(BaseModel):
    image: str
    width: int
    height: int
    client_ts: Optional[str] = None


class LegoBlockCandidate(BaseModel):
    id: str
    color: Literal["black", "white", "red", "blue", "yellow"]
    bbox: List[float]
    confidence: float = 0

    @field_validator("bbox")
    @classmethod
    def lego_bbox_has_four_values(cls, value: List[float]) -> List[float]:
        if len(value) != 4:
            raise ValueError("bbox must contain [x1, y1, x2, y2]")
        return value


class LegoVerificationRequest(BaseModel):
    image: str
    width: int
    height: int
    candidates: List[LegoBlockCandidate] = Field(default_factory=list)


class LegoVerificationResponse(BaseModel):
    verified_colors: List[str] = Field(default_factory=list)
    mode: str
    reason: str
    latency_ms: float


IncomingMessageType = Literal["command.submit", "frame.jpeg", "candidate.select", "tracking.stop"]


class CandidateScore(BaseModel):
    detection_id: str
    score: float
    reasons: List[str] = Field(default_factory=list)


class VerificationDecision(BaseModel):
    selected_detection_id: Optional[str] = None
    score: float = 0
    margin: float = 0
    mode: str
    reason: str
    scores: List[CandidateScore] = Field(default_factory=list)
