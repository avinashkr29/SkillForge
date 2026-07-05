from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_transcription_model: str = Field(default="gpt-4o-transcribe", alias="OPENAI_TRANSCRIPTION_MODEL")
    openai_language_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_LANGUAGE_MODEL")
    openai_vision_model: Optional[str] = Field(default=None, alias="OPENAI_VISION_MODEL")
    yoloe_model_path: str = Field(default="yoloe-26s-seg.pt", alias="YOLOE_MODEL_PATH")
    tracker_type: str = Field(default="botsort.yaml", alias="TRACKER_TYPE")
    detector_confidence: float = Field(default=0.08, alias="DETECTOR_CONFIDENCE")
    detector_imgsz: int = Field(default=640, alias="DETECTOR_IMGSZ")
    lost_frame_buffer: int = Field(default=12, alias="LOST_FRAME_BUFFER")
    visual_context_verifier: bool = Field(default=True, alias="VISUAL_CONTEXT_VERIFIER")
    context_auto_lock_min_score: float = Field(default=0.62, alias="CONTEXT_AUTO_LOCK_MIN_SCORE")
    context_auto_lock_margin: float = Field(default=0.14, alias="CONTEXT_AUTO_LOCK_MARGIN")
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
