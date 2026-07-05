from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from skillforge_api.gbrain.connector import GBrainConnector
from skillforge_api.main import app
from skillforge_api.store import SkillForgeStore
from skillforge_api.structuring.engine import StructuringEngine

REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_DIR = REPO_ROOT / "data" / "gbrain-mock"


@pytest.fixture
def connector():
    return GBrainConnector(mock_dir=MOCK_DIR)


def test_mock_gbrain_loads_product_documents(connector):
    docs = connector.list_documents()
    assert len(docs) >= 2
    product_codes = {doc.product_code for doc in docs}
    assert "PRODUCT-1" in product_codes
    assert "PRODUCT-2" in product_codes


def test_structuring_extracts_lego_steps(connector):
    engine = StructuringEngine()
    product_2 = next(doc for doc in connector.list_documents() if doc.product_code == "PRODUCT-2")
    skill = engine.structure(product_2)

    assert skill.source.document_id.startswith("gb-doc-")
    assert len(skill.steps) == 2
    assert skill.steps[0].verification.source_color == "red"
    assert skill.steps[0].verification.target_color == "white"
    assert skill.steps[1].verification.source_color == "yellow"
    assert skill.steps[1].verification.target_color == "red"


@asynccontextmanager
async def _initialized_app():
    connector = GBrainConnector(mock_dir=MOCK_DIR)
    structuring = StructuringEngine()
    store = SkillForgeStore()
    for document in connector.list_documents():
        store.upsert_skill_unit(structuring.structure(document))

    app.state.gbrain = connector
    app.state.structuring = structuring
    app.state.store = store
    yield app


@pytest.mark.anyio
async def test_api_sync_and_assign():
    async with _initialized_app():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            docs = await client.get("/api/gbrain/documents")
            assert docs.status_code == 200
            assert docs.json()["source"] == "gbrain"

            skills = await client.get("/api/skills")
            assert skills.status_code == 200
            assert skills.json()["count"] >= 2

            assignment = await client.post(
                "/api/assignments",
                json={
                    "employeeId": "emp-001",
                    "skillUnitId": "skill-product-1",
                    "assignedBy": "manager",
                },
            )
            assert assignment.status_code == 200
            assert assignment.json()["sourcedFrom"] == "gbrain"

            readiness = await client.get("/api/readiness")
            assert readiness.status_code == 200
            assert readiness.json()["knowledgeSource"] == "gbrain"