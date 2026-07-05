from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import (
    CandidateResolution,
    CandidateSelectionRequest,
    FramePayload,
    Intent,
    LegoVerificationRequest,
    LegoVerificationResponse,
    Metrics,
    ResolverStatus,
    SessionState,
    TargetStatus,
    TypedCommandRequest,
)
from app.modules.candidate_resolver import CandidateResolver
from app.modules.candidate_verifier import CandidateVerifier
from app.modules.command_parser import ObjectCommandParser
from app.modules.coordinates import Point, Size, display_point_to_frame
from app.modules.detector import YOLOEObjectDetector, decode_base64_jpeg
from app.modules.lego_verifier import LegoBlockVerifier
from app.modules.message_bus import WebSocketMessageBus
from app.modules.prompt_manager import PromptManager
from app.modules.session_controller import TrackingSessionController
from app.modules.speech_transcriber import SpeechTranscriber
from app.modules.tracker import TargetTracker


settings = get_settings()
app = FastAPI(title="ActionShare Object Grounding Module", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "detector_model_path": settings.yoloe_model_path,
        "tracker_type": settings.tracker_type,
        "openai_configured": bool(settings.openai_api_key),
        "openai_vision_model": settings.openai_vision_model or settings.openai_language_model,
        "visual_context_verifier": settings.visual_context_verifier,
        "detector_confidence": settings.detector_confidence,
    }


@app.post("/api/commands/parse")
def parse_command(request: TypedCommandRequest) -> Dict[str, Any]:
    parser = ObjectCommandParser(settings)
    parsed, latency_ms = parser.parse(request.text)
    return {"command": parsed.model_dump(mode="json"), "latency_ms": latency_ms}


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")
    transcriber = SpeechTranscriber(settings)
    result, latency_ms = await transcriber.transcribe_upload(file)
    return {"transcription": result.model_dump(mode="json"), "latency_ms": latency_ms}


@app.post("/api/lego/verify")
def verify_lego_blocks(request: LegoVerificationRequest) -> Dict[str, Any]:
    if not request.candidates:
        return LegoVerificationResponse(
            verified_colors=[],
            mode="no-candidates",
            reason="No local color block candidates were present.",
            latency_ms=0,
        ).model_dump(mode="json")
    frame = decode_base64_jpeg(request.image)
    verifier = LegoBlockVerifier(settings)
    result = verifier.verify(frame, request.candidates)
    return result.model_dump(mode="json")


@app.websocket("/ws/teaching")
async def teaching_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    bus = WebSocketMessageBus(websocket)
    controller = TrackingSessionController()
    parser = ObjectCommandParser(settings)
    prompt_manager = PromptManager()
    detector = YOLOEObjectDetector(settings)
    resolver = CandidateResolver(confidence_threshold=settings.detector_confidence)
    verifier = CandidateVerifier(settings)
    tracker = TargetTracker(lost_frame_buffer=settings.lost_frame_buffer)
    metrics = Metrics()
    current_candidates = []
    active_object_phrase = ""
    frame_id = 0
    last_frame_started: Optional[float] = None
    transcript_final_at: Optional[float] = None

    async def send_state(reason: str) -> None:
        transition, transition_reason = controller.latest_transition()
        await bus.send(
            "session.state",
            {
                "state": controller.state.value,
                "reason": reason,
                "transition": transition,
                "transition_reason": transition_reason,
            },
        )

    async def transition(next_state: SessionState, reason: str) -> None:
        try:
            controller.transition_to(next_state, reason)
            await send_state(reason)
        except ValueError as exc:
            controller.transition_to(SessionState.ERROR, str(exc))
            await bus.send("error", {"message": str(exc)})
            await send_state("Invalid transition")

    await send_state("WebSocket connected")

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            payload = message.get("payload") or {}

            if message_type == "command.submit":
                text = str(payload.get("text", ""))
                await transition(SessionState.PARSING_COMMAND, "Trainer command received")
                parsed, latency_ms = parser.parse(text)
                metrics.command_parsing_latency_ms = latency_ms
                await bus.send("command.parsed", {"command": parsed.model_dump(mode="json"), "latency_ms": latency_ms})

                if parsed.intent == Intent.STOP_TRACKING:
                    tracker.reset()
                    current_candidates = []
                    await transition(SessionState.STOPPED, "Stop tracking command parsed")
                    continue

                if parsed.intent == Intent.UNCLEAR:
                    await bus.send("error", {"message": parsed.reason or "Command is unclear.", "recoverable": True})
                    await transition(SessionState.IDLE, "Command requires clarification")
                    continue

                prompt_manager.apply_command(parsed)
                tracker.reset()
                current_candidates = []
                active_object_phrase = parsed.object_phrase or parsed.base_object or prompt_manager.active_prompts[0]
                transcript_final_at = time.perf_counter()
                await transition(
                    SessionState.SEARCHING,
                    f"Searching for {parsed.object_phrase}",
                )
                continue

            if message_type == "tracking.stop":
                tracker.reset()
                current_candidates = []
                await transition(SessionState.STOPPED, "Tracking stopped by user")
                continue

            if message_type == "candidate.select":
                request = CandidateSelectionRequest.model_validate(payload)
                point = display_point_to_frame(
                    Point(x=request.x, y=request.y),
                    Size(width=request.display_width, height=request.display_height),
                    Size(width=request.frame_width, height=request.frame_height),
                )
                selected = resolver.select_by_point(current_candidates, point)
                if selected is None:
                    await bus.send("error", {"message": "No candidate contains that click.", "recoverable": True})
                    continue
                target = tracker.lock(selected)
                await transition(SessionState.LOCKED, "Candidate selected")
                await bus.send("target.locked", {"target": target.model_dump(mode="json")})
                await transition(SessionState.TRACKING, "Persistent target lock started")
                continue

            if message_type == "frame.jpeg":
                frame_started = time.perf_counter()
                if last_frame_started is not None:
                    delta = frame_started - last_frame_started
                    metrics.video_fps = 1 / delta if delta > 0 else 0
                last_frame_started = frame_started
                frame_id += 1
                frame_payload = FramePayload.model_validate(payload)
                frame = decode_base64_jpeg(frame_payload.image)

                if not prompt_manager.active_prompts:
                    await bus.send("system.metrics", metrics.model_dump(mode="json"), frame_id=frame_id)
                    continue

                output = detector.detect(frame, prompt_manager.active_prompts, prompt_manager.prompt_version)
                metrics.yoloe_inference_latency_ms = output.latency_ms

                if tracker.target is None or controller.state in {SessionState.SEARCHING, SessionState.NEEDS_SELECTION}:
                    resolution = resolver.resolve(output.detections)
                    current_candidates = resolution.candidates
                    verification_payload = None
                    if resolution.status != ResolverStatus.OBJECT_NOT_FOUND and active_object_phrase:
                        decision, verification_latency_ms = verifier.verify(frame, active_object_phrase, resolution.candidates)
                        metrics.context_verification_latency_ms = verification_latency_ms
                        verification_payload = decision.model_dump(mode="json")
                        if decision.selected_detection_id:
                            resolution = CandidateResolution(
                                status=ResolverStatus.AUTO_LOCKED,
                                selected_detection_id=decision.selected_detection_id,
                                candidates=resolution.candidates,
                            )
                            await bus.send(
                                "candidate.verified",
                                {"verification": verification_payload, "object_phrase": active_object_phrase},
                                frame_id=frame_id,
                            )
                        elif len(resolution.candidates) == 1:
                            resolution = CandidateResolution(
                                status=ResolverStatus.OBJECT_NOT_FOUND,
                                selected_detection_id=None,
                                candidates=resolution.candidates,
                            )
                    await bus.send(
                        "detection.candidates",
                        {
                            "resolution": resolution.model_dump(mode="json"),
                            "detector_backend": output.backend,
                            "prompts": prompt_manager.active_prompts,
                            "verification": verification_payload,
                        },
                        frame_id=frame_id,
                    )
                    if resolution.status == ResolverStatus.AUTO_LOCKED and resolution.selected_detection_id:
                        selected = next(
                            candidate
                            for candidate in resolution.candidates
                            if candidate.detection_id == resolution.selected_detection_id
                        )
                        target = tracker.lock(selected)
                        if transcript_final_at:
                            metrics.transcript_to_first_detection_ms = (time.perf_counter() - transcript_final_at) * 1000
                        lock_reason = "Context verifier auto locked target" if verification_payload else "Single candidate auto locked"
                        await transition(SessionState.LOCKED, lock_reason)
                        await bus.send("target.locked", {"target": target.model_dump(mode="json")}, frame_id=frame_id)
                        await transition(SessionState.TRACKING, "Persistent target lock started")
                    elif resolution.status == ResolverStatus.NEEDS_SELECTION:
                        await transition(SessionState.NEEDS_SELECTION, "Multiple candidates need trainer selection")
                    else:
                        await transition(SessionState.SEARCHING, "Object not found in this frame")
                else:
                    update_started = time.perf_counter()
                    target = tracker.update(output.detections)
                    metrics.tracking_update_latency_ms = (time.perf_counter() - update_started) * 1000
                    metrics.id_switches = tracker.id_switches
                    metrics.lost_and_reacquired_count = tracker.lost_and_reacquired_count
                    if target is not None:
                        if target.status == TargetStatus.TRACKING:
                            if controller.state != SessionState.TRACKING:
                                await transition(SessionState.TRACKING, "Target reacquired")
                            await bus.send("target.updated", {"target": target.model_dump(mode="json")}, frame_id=frame_id)
                        elif target.status == TargetStatus.TEMPORARILY_LOST:
                            if controller.state != SessionState.TEMPORARILY_LOST:
                                await transition(SessionState.TEMPORARILY_LOST, "Target temporarily lost")
                            await bus.send("target.temporarily_lost", {"target": target.model_dump(mode="json")}, frame_id=frame_id)
                        elif target.status == TargetStatus.LOST:
                            if controller.state != SessionState.LOST:
                                await transition(SessionState.LOST, "Target lost")
                            await bus.send("target.lost", {"target": target.model_dump(mode="json")}, frame_id=frame_id)

                await bus.send("system.metrics", metrics.model_dump(mode="json"), frame_id=frame_id)
                continue

            await bus.send("error", {"message": f"Unsupported message type: {message_type}", "recoverable": True})

    except WebSocketDisconnect:
        return
