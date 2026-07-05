# Architecture

```mermaid
flowchart LR
  Trainer["Trainer"]
  UI["TeachingModeUI React + webcam + overlay"]
  WS["WebSocketMessageBus"]
  API["FastAPI backend"]
  Transcriber["SpeechTranscriber"]
  Parser["ObjectCommandParser"]
  Prompts["PromptManager"]
  Detector["YOLOEObjectDetector"]
  Resolver["CandidateResolver"]
  Tracker["TargetTracker"]
  State["TrackingSessionController"]

  Trainer --> UI
  UI -->|typed command| WS
  UI -->|push-to-talk audio| API
  API --> Transcriber
  Transcriber --> Parser
  WS --> API
  API --> Parser
  Parser --> Prompts
  UI -->|JPEG frames| WS
  Prompts --> Detector
  Detector --> Resolver
  Resolver -->|one candidate| Tracker
  Resolver -->|multiple candidates| UI
  UI -->|click selection| Resolver
  Tracker --> WS
  State --> WS
  WS --> UI
```

## Message Types

- `transcription.final`
- `command.parsed`
- `detection.candidates`
- `target.locked`
- `target.updated`
- `target.temporarily_lost`
- `target.lost`
- `session.state`
- `system.metrics`
- `error`
