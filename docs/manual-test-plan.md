# Manual Test Plan

## Local Bringup

- Start backend on port `8000`.
- Start frontend on port `5173`.
- Open `http://localhost:5173`.
- Start the camera and grant browser camera permission.
- Confirm the top bar shows camera live, WebSocket connected, FPS, and latency.

## Typed Command And Detection

- Put one red object in frame.
- Submit `track red bottle`.
- Confirm the parsed object is `red bottle`.
- Confirm one candidate is auto-locked and the overlay shows a green target box.

## Multiple Candidates

- Put two red objects in frame.
- Submit `track red bottle`.
- Confirm the state becomes `NEEDS_SELECTION`.
- Click one candidate.
- Confirm the selected target receives a track ID.
- Move the selected object and confirm the other object does not steal the target.

## Push To Talk

- Set `OPENAI_API_KEY`.
- Hold the microphone button and say `I am picking up the red bottle`.
- Release the button.
- Confirm the transcript appears and the same parser/detection path starts.

## Error And Ambiguity Handling

- Submit `track this`; confirm the command is marked unclear.
- Submit `stop tracking`; confirm target state clears.
- Submit `track red bottle` with no red object visible; confirm candidates are not locked.
- Hide the tracked object briefly; confirm `TEMPORARILY_LOST`.
- Keep it hidden past `LOST_FRAME_BUFFER`; confirm `LOST`.
- Deny camera permission; confirm a visible camera error event.
- Remove `OPENAI_API_KEY` and try push-to-talk; confirm a recoverable speech error.

## Metrics

- Confirm the side panel updates FPS, detector latency, parse latency, first-box latency, tracking latency, lost/reacquired count, and ID switch count.
