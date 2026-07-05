"""Parse plain-text LEGO assembly instructions into structured steps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_COLORS = frozenset({"red", "yellow", "white", "blue", "green", "orange"})

STEP_PATTERN = re.compile(
    r"step\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s*[:.\-]?\s*"
    r"(?:take\s+)?(\w+)\s+block\s+put\s+on\s+top\s+of\s+(\w+)\s+block",
    re.IGNORECASE,
)

FALLBACK_PATTERN = re.compile(
    r"(?:take\s+)?(\w+)\s+block\s+(?:and\s+)?put\s+on\s+top\s+of\s+(\w+)\s+block",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AssemblyStep:
    number: int
    source_color: str
    target_color: str
    raw_text: str

    @property
    def instruction(self) -> str:
        return (
            f"Take {self.source_color} block and put it on top of "
            f"{self.target_color} block"
        )


def _normalize_color(color: str) -> str:
    normalized = color.strip().lower()
    if normalized not in SUPPORTED_COLORS:
        raise ValueError(
            f"Unsupported block color '{color}'. "
            f"Supported colors: {', '.join(sorted(SUPPORTED_COLORS))}"
        )
    return normalized


def parse_instruction_line(line: str, step_number: int) -> AssemblyStep | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    match = STEP_PATTERN.search(stripped) or FALLBACK_PATTERN.search(stripped)
    if not match:
        return None

    source_color = _normalize_color(match.group(1))
    target_color = _normalize_color(match.group(2))
    return AssemblyStep(
        number=step_number,
        source_color=source_color,
        target_color=target_color,
        raw_text=stripped,
    )


def load_instructions(path: str | Path) -> list[AssemblyStep]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {file_path}")

    steps: list[AssemblyStep] = []
    step_number = 1

    for line in file_path.read_text(encoding="utf-8").splitlines():
        step = parse_instruction_line(line, step_number)
        if step is not None:
            steps.append(step)
            step_number += 1

    if not steps:
        raise ValueError(
            f"No valid steps found in {file_path}. "
            "Expected lines like: step one: take red block put on top of white block"
        )

    return steps