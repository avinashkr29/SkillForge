from __future__ import annotations

import json
import re
import time
from typing import Optional, Tuple

from app.config import Settings
from app.models import Intent, ObjectAttributes, ParsedCommand


COLORS = {
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "pink",
    "black",
    "white",
    "gray",
    "grey",
    "brown",
    "silver",
    "gold",
}
SIZES = {"small", "large", "big", "tiny", "tall", "short", "wide", "narrow"}
MATERIALS = {"metal", "metallic", "wood", "wooden", "plastic", "glass", "rubber", "paper", "cardboard"}
POSITIONS = {"left", "right", "front", "back", "middle", "center", "top", "bottom", "near", "far"}
PRONOUNS = {"this", "that", "it", "these", "those", "thing", "object"}
STOP_WORDS = {
    "please",
    "now",
    "the",
    "a",
    "an",
    "to",
    "for",
    "can",
    "you",
    "could",
    "would",
    "i",
    "am",
    "i'm",
    "im",
    "going",
}
ACTION_PATTERNS = [
    (re.compile(r"\b(pick(?:ing)? up|grab(?:bing)?|lift(?:ing)?|take|taking)\b"), "pick_up"),
    (re.compile(r"\b(track|follow|find|detect|search for|look for)\b"), "track"),
]


def clean_text(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\s-]", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def contains_unresolved_pronoun(text: str) -> bool:
    return bool(PRONOUNS.intersection(clean_text(text).split()))


def extract_after_action(text: str) -> Tuple[Optional[str], Optional[str]]:
    cleaned = clean_text(text)
    action_context: Optional[str] = None
    best_start = -1
    best_match = None

    for pattern, action in ACTION_PATTERNS:
        for match in pattern.finditer(cleaned):
            if match.end() > best_start:
                best_start = match.end()
                best_match = match
                action_context = action

    if best_match is None:
        return cleaned, None

    phrase = cleaned[best_match.end() :].strip()
    phrase = re.sub(r"^(the|a|an)\s+", "", phrase)
    return phrase, action_context


def trim_action_noise(phrase: str) -> str:
    phrase = clean_text(phrase)
    phrase = re.sub(r"\b(i am|i'm|im|going to|want to|trying to)\b", " ", phrase)
    phrase = re.sub(r"\b(track|follow|find|detect|search for|look for)\b", " ", phrase)
    phrase = re.sub(r"\b(picking up|pick up|grabbing|grab|lifting|lift|taking|take|holding|hold)\b", " ", phrase)
    tokens = [token for token in phrase.split() if token not in STOP_WORDS]
    return " ".join(tokens)


def infer_attributes(tokens: list[str]) -> ObjectAttributes:
    return ObjectAttributes(
        color=next((token for token in tokens if token in COLORS), None),
        size=next((token for token in tokens if token in SIZES), None),
        material=next((token for token in tokens if token in MATERIALS), None),
        position=next((token for token in tokens if token in POSITIONS), None),
    )


def infer_base_object(tokens: list[str]) -> Optional[str]:
    visual_attribute_tokens = COLORS | SIZES | MATERIALS | POSITIONS
    base_tokens = [token for token in tokens if token not in visual_attribute_tokens and token not in STOP_WORDS]
    if not base_tokens:
        return None
    return " ".join(base_tokens[-2:]) if len(base_tokens) > 1 else base_tokens[0]


class ObjectCommandParser:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai_client = None

    def parse(self, transcript: str) -> tuple[ParsedCommand, float]:
        started = time.perf_counter()
        parsed = self._parse_with_openai(transcript) or self.parse_deterministic(transcript)
        latency_ms = (time.perf_counter() - started) * 1000
        return parsed, latency_ms

    def parse_deterministic(self, transcript: str) -> ParsedCommand:
        cleaned = clean_text(transcript)
        if not cleaned:
            return ParsedCommand(
                intent=Intent.UNCLEAR,
                requires_confirmation=True,
                reason="No command was provided.",
            )

        if re.search(r"\b(stop|cancel|clear|end)\b", cleaned) and "tracking" in cleaned:
            return ParsedCommand(intent=Intent.STOP_TRACKING, reason="Stop tracking command detected.")

        if contains_unresolved_pronoun(cleaned):
            return ParsedCommand(
                intent=Intent.UNCLEAR,
                object_phrase=None,
                base_object=None,
                requires_confirmation=True,
                reason="The command uses an unresolved pronoun.",
            )

        raw_phrase, action_context = extract_after_action(cleaned)
        object_phrase = trim_action_noise(raw_phrase or cleaned)
        tokens = object_phrase.split()
        base_object = infer_base_object(tokens)

        if not object_phrase or not base_object:
            return ParsedCommand(
                intent=Intent.UNCLEAR,
                object_phrase=object_phrase or None,
                base_object=base_object,
                requires_confirmation=True,
                reason="No visually meaningful object name was found.",
            )

        return ParsedCommand(
            intent=Intent.TRACK_OBJECT,
            object_phrase=object_phrase,
            base_object=base_object,
            attributes=infer_attributes(tokens),
            action_context=action_context,
            requires_confirmation=False,
            reason="Parsed with deterministic fallback.",
        )

    def _parse_with_openai(self, transcript: str) -> Optional[ParsedCommand]:
        if not self.settings.openai_api_key:
            return None
        try:
            from openai import OpenAI
        except Exception:
            return None

        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self.settings.openai_api_key)

        schema = ParsedCommand.model_json_schema()
        system_prompt = (
            "Extract only visually meaningful object descriptions for ActionShare teaching mode. "
            "Return intent track_object, stop_tracking, or unclear. Do not invent object names. "
            "If this, that, it, these, or those is unresolved, return unclear and requires_confirmation true."
        )
        try:
            response = self._openai_client.responses.create(
                model=self.settings.openai_language_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "object_command",
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
            output_text = getattr(response, "output_text", None)
            if not output_text:
                return None
            return ParsedCommand.model_validate(json.loads(output_text))
        except Exception:
            return None
