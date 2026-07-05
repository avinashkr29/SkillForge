# API Service

Backend service handling GBrain synchronization, AI structuring, computer vision verification, and readiness scoring.

## Purpose

- **GBrain Connector** — authenticate and pull company documents
- **AI Structuring Engine** — convert documents and expert videos into skill units
- **CV Verification** — analyze camera frames against step success criteria
- **Readiness Scoring** — aggregate practice session results into readiness metrics

## Planned Tech

- Python (FastAPI) or Node.js — TBD during Phase 2 scaffolding
- GBrain API client
- AI/ML pipeline for document and video structuring
- Computer vision model for step verification

## Dependencies

- `packages/shared` — skill unit schema and validation
- GBrain API (external)
- AI/ML services for structuring and verification (external)

## Status

**GBrain mock connector implemented (Phase 2 starter).**

| Component | Status |
|-----------|--------|
| GBrain connector (mock) | ✅ `skillforge_api/gbrain/connector.py` |
| Structuring engine | ✅ GBrain SOP → skill unit |
| Assignments API | ✅ Manager assigns skills to employees |
| Readiness API | ✅ Skill gaps per employee |
| Manager portal | ✅ `/manager` |
| Employee portal | ✅ `/employee` |

## Quick start

```bash
cd services/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../../packages/shared/python -e ".[dev]"
uvicorn skillforge_api.main:app --reload --port 8000
```

Mock GBrain documents live in `data/gbrain-mock/`. Override with `GBRAIN_MOCK_DIR`.