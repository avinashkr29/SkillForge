# SkillForge — Agent Guide

## Knowledge source: official GBrain

Manufacturing procedures live in `brain/manufacturing/`. They are indexed by [GBrain](https://github.com/garrytan/gbrain) and synced into SkillForge skill units.

- Setup: [docs/gstack-integration.md](docs/gstack-integration.md)
- GStack install: `/setup-gbrain` from [garrytan/gstack](https://github.com/garrytan/gstack)
- Brain import: `gbrain import brain/` or `./scripts/setup-gbrain.sh`

## GBrain search guidance

Before implementing procedure or verification changes:

1. Read `brain/manufacturing/` SOP pages for Product 1 and Product 2
2. If `gbrain` is on PATH, prefer `gbrain search "..."` and `gbrain get manufacturing/<slug>`
3. Keep SkillForge as the **execution layer** — GBrain remains the knowledge source

## Run locally

```bash
# API + portals
cd services/api && uvicorn skillforge_api.main:app --reload --port 8000

# LEGO AR verification
cd services/cv-verification && python -m lego_ar
```

## Connector status

`GET /api/gbrain/status` reports whether the official `gbrain` CLI is active or filesystem fallback is in use.