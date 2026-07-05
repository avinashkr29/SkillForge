from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from app.models import ParsedCommand


def normalize_prompt(prompt: str) -> str:
    prompt = re.sub(r"[^a-zA-Z0-9\s-]", " ", prompt.lower())
    prompt = re.sub(r"\b(the|a|an)\b", " ", prompt)
    return re.sub(r"\s+", " ", prompt).strip()


def dedupe_prompts(prompts: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for prompt in prompts:
        normalized = normalize_prompt(prompt)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


@dataclass
class PromptManager:
    active_prompts: List[str] = field(default_factory=list)
    prompt_version: int = 0
    updated_at: Optional[datetime] = None
    _last_key: str = ""
    _last_transcript: str = ""

    def apply_command(self, command: ParsedCommand) -> bool:
        phrase = command.object_phrase or ""
        base = command.base_object or ""
        prompts = dedupe_prompts([*self._progressive_attribute_fallbacks(phrase), base])
        key = "|".join(prompts)
        if not prompts or key == self._last_key:
            return False
        self.active_prompts = prompts
        self.prompt_version += 1
        self.updated_at = datetime.now(timezone.utc)
        self._last_key = key
        return True

    def should_ignore_duplicate_transcript(self, transcript: str) -> bool:
        normalized = normalize_prompt(transcript)
        if normalized and normalized == self._last_transcript:
            return True
        self._last_transcript = normalized
        return False

    @staticmethod
    def _progressive_attribute_fallbacks(phrase: str) -> List[str]:
        attribute_words = {
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
            "small",
            "large",
            "big",
            "tiny",
            "metal",
            "metallic",
            "wood",
            "wooden",
            "plastic",
            "glass",
        }
        tokens = normalize_prompt(phrase).split()
        prompts = [" ".join(tokens)] if tokens else []
        while tokens and tokens[0] in attribute_words:
            tokens.pop(0)
            if tokens:
                prompts.append(" ".join(tokens))
        return prompts
