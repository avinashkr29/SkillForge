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

Not yet implemented. GBrain connector planned for Phase 2.