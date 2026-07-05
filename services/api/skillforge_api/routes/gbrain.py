from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/gbrain", tags=["gbrain"])


@router.get("/documents")
def list_gbrain_documents(request: Request):
    connector = request.app.state.gbrain
    return {
        "source": "gbrain",
        "documents": [doc.model_dump(by_alias=True) for doc in connector.list_documents()],
    }


@router.get("/documents/{document_id}")
def get_gbrain_document(document_id: str, request: Request):
    connector = request.app.state.gbrain
    document = connector.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="GBrain document not found")
    return {"source": "gbrain", "document": document.model_dump(by_alias=True)}


@router.get("/search")
def search_gbrain_documents(q: str, request: Request):
    connector = request.app.state.gbrain
    results = connector.search_documents(q)
    return {
        "source": "gbrain",
        "query": q,
        "documents": [doc.model_dump(by_alias=True) for doc in results],
    }


@router.post("/sync/{document_id}")
def sync_gbrain_document(document_id: str, request: Request):
    connector = request.app.state.gbrain
    structuring = request.app.state.structuring
    store = request.app.state.store

    document = connector.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="GBrain document not found")

    skill_unit = structuring.structure(document)
    store.upsert_skill_unit(skill_unit)

    return {
        "source": "gbrain",
        "message": f"Synced '{document.title}' from GBrain into SkillForge",
        "skillUnit": skill_unit.model_dump(by_alias=True),
    }


@router.post("/sync-all")
def sync_all_gbrain_documents(request: Request):
    connector = request.app.state.gbrain
    structuring = request.app.state.structuring
    store = request.app.state.store

    synced = []
    for document in connector.list_documents():
        skill_unit = structuring.structure(document)
        store.upsert_skill_unit(skill_unit)
        synced.append(skill_unit.model_dump(by_alias=True))

    return {
        "source": "gbrain",
        "message": f"Synced {len(synced)} document(s) from GBrain",
        "skillUnits": synced,
    }