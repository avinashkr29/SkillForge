from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["assignments"])


class AssignSkillRequest(BaseModel):
    employee_id: str = Field(alias="employeeId")
    skill_unit_id: str = Field(alias="skillUnitId")
    assigned_by: str = Field(default="manager", alias="assignedBy")

    model_config = {"populate_by_name": True}


class UpdateProgressRequest(BaseModel):
    status: str
    readiness_score: float | None = Field(default=None, alias="readinessScore")

    model_config = {"populate_by_name": True}


@router.get("/employees")
def list_employees(request: Request):
    store = request.app.state.store
    return {
        "employees": [emp.model_dump() for emp in store.list_employees()],
    }


@router.get("/assignments")
def list_assignments(request: Request, employee_id: str | None = None):
    store = request.app.state.store
    assignments = store.list_assignments(employee_id)
    return {
        "assignments": [a.model_dump(by_alias=True) for a in assignments],
    }


@router.post("/assignments")
def assign_skill(payload: AssignSkillRequest, request: Request):
    store = request.app.state.store
    try:
        assignment = store.assign_skill(
            payload.employee_id,
            payload.skill_unit_id,
            payload.assigned_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    skill = store.get_skill_unit(payload.skill_unit_id)
    return {
        "message": f"Assigned '{skill.title if skill else payload.skill_unit_id}' to employee",
        "assignment": assignment.model_dump(by_alias=True),
        "sourcedFrom": "gbrain" if skill else None,
    }


@router.patch("/assignments/{assignment_id}")
def update_assignment(
    assignment_id: str,
    payload: UpdateProgressRequest,
    request: Request,
):
    store = request.app.state.store
    if assignment_id not in store.assignments:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment = store.update_assignment_progress(
        assignment_id,
        payload.status,
        payload.readiness_score,
    )
    return assignment.model_dump(by_alias=True)


@router.get("/readiness")
def readiness_dashboard(request: Request):
    store = request.app.state.store
    reports = store.readiness_reports()
    return {
        "source": "skillforge",
        "knowledgeSource": "gbrain",
        "reports": [report.model_dump(by_alias=True) for report in reports],
    }