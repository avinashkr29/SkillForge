"""SkillForge API — GBrain-first skill extraction and assignment."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from skillforge_api.gbrain.connector import GBrainConnector
from skillforge_api.routes import assignments, gbrain, skills
from skillforge_api.store import SkillForgeStore
from skillforge_api.structuring.engine import StructuringEngine

REPO_ROOT = Path(__file__).resolve().parents[3]
MANAGER_UI = REPO_ROOT / "apps" / "manager" / "public"
EMPLOYEE_UI = REPO_ROOT / "apps" / "employee" / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    connector = GBrainConnector()
    structuring = StructuringEngine()
    store = SkillForgeStore()

    for document in connector.list_documents():
        store.upsert_skill_unit(structuring.structure(document))

    app.state.gbrain = connector
    app.state.structuring = structuring
    app.state.store = store
    yield


app = FastAPI(
    title="SkillForge API",
    description="Execution layer on top of GBrain — extract skills, assign training, track readiness",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gbrain.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(assignments.router, prefix="/api")

if MANAGER_UI.exists():
    app.mount("/manager", StaticFiles(directory=MANAGER_UI, html=True), name="manager")
if EMPLOYEE_UI.exists():
    app.mount("/employee", StaticFiles(directory=EMPLOYEE_UI, html=True), name="employee")


@app.get("/")
def root():
    return {
        "name": "SkillForge",
        "tagline": "Turn GBrain knowledge into executable skills",
        "knowledgeSource": "gbrain",
        "portals": {
            "manager": "/manager",
            "employee": "/employee",
        },
        "api": {
            "gbrainDocuments": "/api/gbrain/documents",
            "skills": "/api/skills",
            "assignments": "/api/assignments",
            "readiness": "/api/readiness",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "gbrain": "connected-mock"}