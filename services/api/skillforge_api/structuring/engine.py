"""Convert GBrain documents into executable SkillForge skill units."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from skillforge_shared.models import (
    GBrainDocument,
    ReadinessWeights,
    SafetyLevel,
    SkillSource,
    SkillStep,
    SkillUnit,
    SourceType,
    StepVerification,
)

COLOR_PATTERN = re.compile(
    r"take the \*\*(\w+) block\*\* and place it on top of the \*\*(\w+) block\*\*",
    re.IGNORECASE,
)


class StructuringEngine:
    """Extracts ordered procedural steps from GBrain SOP documents."""

    def structure(self, document: GBrainDocument) -> SkillUnit:
        steps = self._parse_steps(document.content)
        if not steps:
            raise ValueError(f"No assembly steps found in GBrain document {document.id}")

        skill_id = f"skill-{document.product_code.lower().replace('_', '-')}"
        return SkillUnit(
            id=skill_id,
            title=document.title,
            version="1.0.0",
            productCode=document.product_code,
            source=SkillSource(
                type=SourceType.GBRAIN_DOCUMENT,
                documentId=document.id,
                title=document.title,
                syncedAt=datetime.now(timezone.utc),
            ),
            safetyLevel=SafetyLevel.LOW,
            estimatedDurationMinutes=max(10, len(steps) * 5),
            steps=steps,
            readinessWeights=ReadinessWeights(),
        )

    def _parse_steps(self, content: str) -> list[SkillStep]:
        if "### Step" in content:
            return self._parse_legacy_step_sections(content)
        return self._parse_gbrain_timeline(content)

    def _parse_legacy_step_sections(self, content: str) -> list[SkillStep]:
        steps: list[SkillStep] = []
        sections = re.split(r"### Step \d+:\s*", content)

        for index, section in enumerate(sections[1:], start=1):
            step = self._build_step_from_section(index, section)
            if step is not None:
                steps.append(step)
        return steps

    def _parse_gbrain_timeline(self, content: str) -> list[SkillStep]:
        steps: list[SkillStep] = []
        sections = re.split(r"###\s+", content)

        for index, section in enumerate(sections[1:], start=1):
            if not COLOR_PATTERN.search(section):
                continue
            step = self._build_step_from_section(index, section)
            if step is not None:
                steps.append(step)

        if steps:
            return steps

        for index, match in enumerate(COLOR_PATTERN.finditer(content), start=1):
            source = match.group(1).lower()
            target = match.group(2).lower()
            instruction = match.group(0)
            steps.append(
                SkillStep(
                    order=index,
                    title=f"Place {source} on {target}",
                    instruction=instruction,
                    successCriteria=[f"{source} block centered on {target} block"],
                    verification=StepVerification(
                        type="visual",
                        sourceColor=source,
                        targetColor=target,
                        checkpoints=[f"{source}_on_{target}", "stack_stable"],
                    ),
                )
            )
        return steps

    def _build_step_from_section(self, index: int, section: str) -> SkillStep | None:
        lines = [line.strip() for line in section.strip().splitlines() if line.strip()]
        if not lines:
            return None

        title = lines[0].rstrip("—").strip()
        instruction = title
        success_criteria: list[str] = []
        verification: StepVerification | None = None

        for line in lines[1:]:
            if line.startswith("- "):
                success_criteria.append(line[2:])
            elif COLOR_PATTERN.search(line):
                instruction = line

        color_match = COLOR_PATTERN.search(section)
        if color_match:
            verification = StepVerification(
                type="visual",
                sourceColor=color_match.group(1).lower(),
                targetColor=color_match.group(2).lower(),
                checkpoints=[
                    f"{color_match.group(1).lower()}_on_{color_match.group(2).lower()}",
                    "stack_stable",
                ],
            )
            instruction = color_match.group(0)

        return SkillStep(
            order=index,
            title=title,
            instruction=instruction,
            successCriteria=success_criteria or [f"Step {index} completed correctly"],
            verification=verification,
        )