# SkillForge Company Brain

Markdown source-of-truth for manufacturing procedures, indexed by [GBrain](https://github.com/garrytan/gbrain).

## Layout

```
brain/
└── manufacturing/     # Assembly SOPs synced into SkillForge skill units
    ├── product-1-assembly.md
    └── product-2-assembly.md
```

Pages follow GBrain's **compiled truth + timeline** pattern. SkillForge reads these pages (via `gbrain get` or direct filesystem) and converts them into executable skill units.

## Index with official GBrain

```bash
# Install (see docs/gstack-integration.md)
bun install -g github:garrytan/gbrain
gbrain init --pglite
gbrain import brain/
gbrain search "product 2 assembly"
```

## Sync from GStack

If you use [GStack](https://github.com/garrytan/gstack), run `/setup-gbrain` once, then `/sync-gbrain` to keep this repo indexed.