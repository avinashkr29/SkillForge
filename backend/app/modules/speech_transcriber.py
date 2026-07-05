from __future__ import annotations

import io
import time
from typing import Tuple

from fastapi import UploadFile

from app.config import Settings
from app.models import TranscriptResult


class SpeechTranscriber:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai_client = None

    async def transcribe_upload(self, upload: UploadFile) -> Tuple[TranscriptResult, float]:
        started = time.perf_counter()
        if not self.settings.openai_api_key:
            return TranscriptResult(transcript="", is_final=True, confidence=None), (time.perf_counter() - started) * 1000
        try:
            from openai import OpenAI
        except Exception as exc:
            raise RuntimeError("OpenAI package is not installed") from exc
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self.settings.openai_api_key)
        audio_bytes = await upload.read()
        filename = upload.filename or "command.webm"
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        response = self._openai_client.audio.transcriptions.create(
            model=self.settings.openai_transcription_model,
            file=file_obj,
        )
        transcript = getattr(response, "text", "") or ""
        return TranscriptResult(transcript=transcript, is_final=True, confidence=None), (time.perf_counter() - started) * 1000
