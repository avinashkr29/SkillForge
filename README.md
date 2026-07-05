# SkillForge LEGO Assembly Skills

## Overview

This repository contains **SkillForge skill documentation** for LEGO assembly tasks. SkillForge is an AI-powered platform that converts organizational knowledge into structured, executable skills with real-time verification.

We currently provide two foundational LEGO assembly skills:

1. **Red-Blue-Green Tower** - Stack blocks in RGB sequence
2. **Yellow-Purple-Orange Tower** - Stack blocks in YPO sequence

## Quick Start

### Skills Available

```
skills/
├── lego-assembly-red-blue-green/     # Red → Blue → Green stacking
│   ├── README.md                      # Skill overview & steps
│   └── steps.json                     # Structured step definitions
└── lego-assembly-yellow-purple-orange/ # Yellow → Purple → Orange stacking
    ├── README.md                      # Skill overview & steps
    └── steps.json                     # Structured step definitions
```

## Architecture

### SkillForge (Leader)
- Defines skill steps and sequences
- Manages learner experience and UI
- Orchestrates the overall workflow
- Tracks learner progress

### YOLO (Support - Object Detection)
- Detects colored LEGO blocks in real-time
- Verifies correct sequencing
- Confirms block placement
- Provides real-time feedback

For details, see [YOLO Integration Guide](docs/YOLO_INTEGRATION.md)

## Documentation

- **[Skills Directory](skills/)** - Skill definitions and step documentation
- **[YOLO Integration](docs/YOLO_INTEGRATION.md)** - How YOLO verifies skills
- **[Architecture](docs/architecture.md)** - System architecture (from ActionShare module)

## Technology Stack

- **Frontend**: React/TypeScript
- **Backend**: FastAPI (Python)
- **Object Detection**: YOLO (Ultralytics)
- **Framework**: SkillForge (Anthropic)

## Project Structure

```text
skills/                     # SkillForge skill documentation
docs/                       # Architecture and integration docs
backend/                    # FastAPI backend (object detection support)
frontend/                   # React UI (skill practice interface)
sample_videos/              # Sample LEGO assembly videos
scripts/                    # Utility scripts
```

## Local Development Setup

### Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Access the UI at [http://localhost:5173](http://localhost:5173)

## Configuration

Copy `backend/.env.example` to `backend/.env`:

```bash
cd backend
cp .env.example .env
```

Set your OpenAI API key:
```env
OPENAI_API_KEY=your_key_here
```

## Optional: Install YOLO Detection

For advanced object detection capabilities:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-yolo.txt
```

## Testing

### Backend Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
npm run build
```

## Integration with GBrain

This skill documentation is designed to be integrated with **GBrain** for:
- Automatic skill extraction from company documentation
- Synchronization with SkillForge platform
- Cross-team skill sharing and discovery

Documentation format follows SkillForge standards for seamless GBrain integration.

## Status

- ✅ Core skill definitions created (v0.1)
- 🔄 YOLO integration in progress
- 📋 Awaiting full GBrain sync
- 🚀 Ready for pilot testing with learners

## Next Steps

1. Fill in detailed step photographs/videos
2. Configure YOLO model for production
3. Test with real learners
4. Sync with GBrain for broader distribution
5. Expand to additional LEGO assembly products

## License

MIT

---
**Last Updated**: 2026-07-05  
**Framework**: SkillForge (Anthropic)
