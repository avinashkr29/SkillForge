# Shared Package

Single source of truth for types, schemas, and design tokens used across all SkillForge apps and services.

## Purpose

- Skill unit JSON schema and TypeScript/Python type definitions
- Shared validation logic for procedural steps and success criteria
- UI design tokens (colors, typography, spacing) for consistent branding
- Common utility functions (readiness score calculation, step ordering)

## Planned Contents

```
packages/shared/
├── schema/
│   └── skill-unit.json      # JSON Schema for skill units
├── types/
│   └── skill-unit.ts        # TypeScript interfaces
└── tokens/
    └── design-tokens.json   # Shared UI tokens
```

## Dependencies

None — this is the foundation package. All other packages depend on it.

## Status

Not yet implemented. Schema definition planned for Phase 1.