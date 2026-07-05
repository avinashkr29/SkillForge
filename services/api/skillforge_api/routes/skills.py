from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
def list_skills(request: Request):
    store = request.app.state.store
    skills = store.list_skill_units()
    return {
        "skills": [skill.model_dump(by_alias=True) for skill in skills],
        "count": len(skills),
    }


@router.get("/{skill_id}")
def get_skill(skill_id: str, request: Request):
    store = request.app.state.store
    skill = store.get_skill_unit(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill unit not found")
    return skill.model_dump(by_alias=True)


@router.get("/{skill_id}/instructions.txt")
def get_skill_instructions_file(skill_id: str, request: Request):
    """Export skill steps as plain text for the LEGO AR verifier."""
    store = request.app.state.store
    skill = store.get_skill_unit(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill unit not found")

    lines = [f"# {skill.title} — sourced from GBrain", ""]
    for step in skill.steps:
        verification = step.verification
        if verification and verification.source_color and verification.target_color:
            word = _number_word(step.order)
            lines.append(
                f"step {word}: take {verification.source_color} block "
                f"put on top of {verification.target_color} block"
            )
        else:
            lines.append(f"step {step.order}: {step.instruction}")

    return "\n".join(lines) + "\n"


def _number_word(order: int) -> str:
    words = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
    }
    return words.get(order, str(order))