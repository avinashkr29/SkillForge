"""In-memory store for skill units, employees, and assignments."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from skillforge_shared.models import (
    EmployeeProfile,
    ReadinessReport,
    SkillAssignment,
    SkillUnit,
)


class SkillForgeStore:
    def __init__(self) -> None:
        self.skill_units: dict[str, SkillUnit] = {}
        self.assignments: dict[str, SkillAssignment] = {}
        self.employees: dict[str, EmployeeProfile] = {
            "emp-001": EmployeeProfile(
                id="emp-001",
                name="Alex Chen",
                role="Assembly Operator",
                team="Manufacturing",
            ),
            "emp-002": EmployeeProfile(
                id="emp-002",
                name="Jordan Lee",
                role="Assembly Operator",
                team="Manufacturing",
            ),
            "emp-003": EmployeeProfile(
                id="emp-003",
                name="Sam Rivera",
                role="Trainee",
                team="Manufacturing",
            ),
        }

    def upsert_skill_unit(self, skill_unit: SkillUnit) -> SkillUnit:
        self.skill_units[skill_unit.id] = skill_unit
        return skill_unit

    def list_skill_units(self) -> list[SkillUnit]:
        return sorted(self.skill_units.values(), key=lambda unit: unit.title)

    def get_skill_unit(self, skill_unit_id: str) -> SkillUnit | None:
        return self.skill_units.get(skill_unit_id)

    def list_employees(self) -> list[EmployeeProfile]:
        return list(self.employees.values())

    def assign_skill(
        self,
        employee_id: str,
        skill_unit_id: str,
        assigned_by: str,
    ) -> SkillAssignment:
        if employee_id not in self.employees:
            raise KeyError(f"Unknown employee: {employee_id}")
        if skill_unit_id not in self.skill_units:
            raise KeyError(f"Unknown skill unit: {skill_unit_id}")

        assignment = SkillAssignment(
            id=f"asgn-{uuid4().hex[:8]}",
            employeeId=employee_id,
            skillUnitId=skill_unit_id,
            assignedBy=assigned_by,
            assignedAt=datetime.now(timezone.utc),
            status="assigned",
        )
        self.assignments[assignment.id] = assignment
        return assignment

    def list_assignments(
        self,
        employee_id: str | None = None,
    ) -> list[SkillAssignment]:
        assignments = list(self.assignments.values())
        if employee_id:
            assignments = [a for a in assignments if a.employee_id == employee_id]
        return sorted(assignments, key=lambda a: a.assigned_at, reverse=True)

    def update_assignment_progress(
        self,
        assignment_id: str,
        status: str,
        readiness_score: float | None = None,
    ) -> SkillAssignment:
        assignment = self.assignments[assignment_id]
        assignment.status = status  # type: ignore[assignment]
        if readiness_score is not None:
            assignment.readiness_score = readiness_score
        return assignment

    def readiness_reports(self) -> list[ReadinessReport]:
        reports: list[ReadinessReport] = []

        for employee in self.employees.values():
            employee_assignments = self.list_assignments(employee.id)
            completed = [a for a in employee_assignments if a.status == "completed"]
            scores = [
                a.readiness_score
                for a in employee_assignments
                if a.readiness_score is not None
            ]
            average = sum(scores) / len(scores) if scores else 0.0

            skill_gaps: list[str] = []
            for assignment in employee_assignments:
                if assignment.status != "completed":
                    skill = self.skill_units.get(assignment.skill_unit_id)
                    if skill:
                        skill_gaps.append(skill.title)

            reports.append(
                ReadinessReport(
                    employeeId=employee.id,
                    employeeName=employee.name,
                    assignedSkills=len(employee_assignments),
                    completedSkills=len(completed),
                    averageReadiness=round(average, 1),
                    skillGaps=skill_gaps,
                )
            )

        return reports