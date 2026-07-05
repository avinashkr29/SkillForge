# SkillForge Integration Stack

> **Note:** This is SkillForge's layered integration plan — **not** the same as [GStack](https://github.com/garrytan/gstack) (Garry Tan's Claude Code skill pack). For official GStack + GBrain setup, see [docs/gstack-integration.md](../gstack-integration.md).

## Layer order

| Layer | Scope | Official tool |
|-------|-------|---------------|
| 1 | Skill unit schema (`packages/shared`) | — |
| 2 | GBrain brain repo (`brain/manufacturing/`) | [gbrain](https://github.com/garrytan/gbrain) |
| 3 | GBrain connector + structuring | [gbrain](https://github.com/garrytan/gbrain) |
| 4 | API, assignments, readiness | SkillForge |
| 5 | Manager + employee portals | SkillForge |
| 6 | CV verification (LEGO AR) | SkillForge |

## Branch

Active integration branch: `feat/gbrain-integration` on https://github.com/avinashkr29/SkillForge