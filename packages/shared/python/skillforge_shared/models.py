"""Shared SkillForge data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SafetyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceType(str, Enum):
    GBRAIN_DOCUMENT = "gbrain_document"
    EXPERT_VIDEO = "expert_video"
    MANUAL = "manual"


class SkillSource(BaseModel):
    type: SourceType
    document_id: str = Field(alias="documentId")
    title: str
    synced_at: datetime | None = Field(default=None, alias="syncedAt")

    model_config = {"populate_by_name": True}


class StepVerification(BaseModel):
    type: Literal["visual", "sequence", "compliance"] = "visual"
    source_color: str | None = Field(default=None, alias="sourceColor")
    target_color: str | None = Field(default=None, alias="targetColor")
    checkpoints: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SkillStep(BaseModel):
    order: int
    title: str
    instruction: str
    success_criteria: list[str] = Field(alias="successCriteria")
    verification: StepVerification | None = None

    model_config = {"populate_by_name": True}


class ReadinessWeights(BaseModel):
    sequence_correctness: float = Field(0.4, alias="sequenceCorrectness")
    step_completion: float = Field(0.3, alias="stepCompletion")
    safety_compliance: float = Field(0.2, alias="safetyCompliance")
    quality_score: float = Field(0.1, alias="qualityScore")

    model_config = {"populate_by_name": True}


class SkillUnit(BaseModel):
    id: str
    title: str
    version: str
    product_code: str | None = Field(default=None, alias="productCode")
    source: SkillSource
    safety_level: SafetyLevel = Field(SafetyLevel.LOW, alias="safetyLevel")
    estimated_duration_minutes: int = Field(15, alias="estimatedDurationMinutes")
    steps: list[SkillStep]
    readiness_weights: ReadinessWeights = Field(
        default_factory=ReadinessWeights,
        alias="readinessWeights",
    )

    model_config = {"populate_by_name": True}


class GBrainDocument(BaseModel):
    id: str
    title: str
    product_code: str
    content: str
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime


class EmployeeProfile(BaseModel):
    id: str
    name: str
    role: str
    team: str


class SkillAssignment(BaseModel):
    id: str
    employee_id: str = Field(alias="employeeId")
    skill_unit_id: str = Field(alias="skillUnitId")
    assigned_by: str = Field(alias="assignedBy")
    assigned_at: datetime = Field(alias="assignedAt")
    status: Literal["assigned", "in_progress", "completed"] = "assigned"
    readiness_score: float | None = Field(default=None, alias="readinessScore")

    model_config = {"populate_by_name": True}


class ReadinessReport(BaseModel):
    employee_id: str = Field(alias="employeeId")
    employee_name: str = Field(alias="employeeName")
    assigned_skills: int = Field(alias="assignedSkills")
    completed_skills: int = Field(alias="completedSkills")
    average_readiness: float = Field(alias="averageReadiness")
    skill_gaps: list[str] = Field(alias="skillGaps")

    model_config = {"populate_by_name": True}