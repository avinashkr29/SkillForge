import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Camera,
  CheckCircle2,
  Mic,
  MousePointer2,
  Play,
  Square,
  Wifi,
  WifiOff,
  BarChart3
} from "lucide-react";
import type { BBox } from "./lib/geometry";
import { frameBBoxToDisplay } from "./lib/geometry";
import {
  defaultLegoSteps,
  detectLegoBlocksFromImage,
  identifyProduct,
  LegoBlock,
  parseLegoSteps,
  pickBlockByColor,
  Product
} from "./lib/lego";
import {
  backendHttpUrl,
  backendWsUrl,
  DetectionResult,
  Metrics,
  ParsedCommand,
  SessionState,
  TargetState,
  WsEnvelope
} from "./lib/messages";
import type { LegoVerificationResponse } from "./lib/messages";
import SkillManager from "./SkillManager";
import "./styles.css";

type EventItem = {
  id: string;
  label: string;
  detail: string;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

const emptyMetrics: Metrics = {
  video_fps: 0,
  yoloe_inference_latency_ms: 0,
  context_verification_latency_ms: 0,
  speech_transcription_latency_ms: 0,
  command_parsing_latency_ms: 0,
  transcript_to_first_detection_ms: 0,
  tracking_update_latency_ms: 0,
  id_switches: 0,
  lost_and_reacquired_count: 0
};

function fmt(value: number, digits = 0): string {
  if (!Number.isFinite(value)) {
    return "0";
  }
  return value.toFixed(digits);
}

export default function App() {
  const [viewMode, setViewMode] = useState<"teaching" | "manager">("teaching");

  if (viewMode === "manager") {
    return <SkillManagerWithNav onSwitchMode={() => setViewMode("teaching")} />;
  }

  return <TeachingMode onSwitchMode={() => setViewMode("manager")} />;
}

function TeachingMode({ onSwitchMode }: { onSwitchMode: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const captureRef = useRef<HTMLCanvasElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const eventCounterRef = useRef(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const speechRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const browserSpeechTranscriptRef = useRef("");
  const legoTimerRef = useRef<number | null>(null);
  const legoVerificationRef = useRef({ signature: "", verifiedAt: 0, inFlight: false });

  const [cameraStatus, setCameraStatus] = useState("Off");
  const [connectionStatus, setConnectionStatus] = useState("Disconnected");
  const [cameraDevices, setCameraDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [openAiConfigured, setOpenAiConfigured] = useState<boolean | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>("IDLE");
  const [transcript, setTranscript] = useState("");
  const [parsedCommand, setParsedCommand] = useState<ParsedCommand | null>(null);
  const [candidates, setCandidates] = useState<DetectionResult[]>([]);
  const [target, setTarget] = useState<TargetState | null>(null);
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [legoStepsText, setLegoStepsText] = useState(defaultLegoSteps);
  const [legoStepIndex, setLegoStepIndex] = useState(0);
  const [legoBlocks, setLegoBlocks] = useState<LegoBlock[]>([]);
  const [legoStatus, setLegoStatus] = useState("Start camera to identify color blocks");
  const [legoVerifierMode, setLegoVerifierMode] = useState("-");
  const [detectedProduct, setDetectedProduct] = useState<Product | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<"product-1" | "product-2" | null>(null);

  const legoSteps = useMemo(() => parseLegoSteps(legoStepsText), [legoStepsText]);
  const activeLegoStep = legoSteps[Math.min(legoStepIndex, Math.max(0, legoSteps.length - 1))] ?? null;
  const legoInventory = useMemo(() => {
    const bestByColor = new Map<string, LegoBlock>();
    legoBlocks.forEach((block) => {
      const current = bestByColor.get(block.color);
      if (!current || block.area > current.area) {
        bestByColor.set(block.color, block);
      }
    });
    return Array.from(bestByColor.values())
      .sort((a, b) => a.center.x - b.center.x)
      .map((block) => block.color)
      .join(", ");
  }, [legoBlocks]);
  const legoGuideText = useMemo(() => {
    if (cameraStatus !== "Live") {
      return "Step 1: start camera and show the color blocks.";
    }
    if (!legoBlocks.length) {
      return "Step 1: identifying the color blocks first.";
    }
    const source = pickBlockByColor(legoBlocks, activeLegoStep?.sourceColor ?? null);
    const destination = pickBlockByColor(legoBlocks, activeLegoStep?.targetColor ?? null);
    const missing = [
      activeLegoStep?.sourceColor && !source ? activeLegoStep.sourceColor : null,
      activeLegoStep?.targetColor && !destination ? activeLegoStep.targetColor : null
    ].filter(Boolean);
    if (missing.length) {
      return `Found ${legoInventory || "blocks"}. Need ${missing.join(" and ")} block.`;
    }
    return activeLegoStep ? `Step ${legoStepIndex + 1}: ${activeLegoStep.text}` : `Step 1: found ${legoInventory}.`;
  }, [activeLegoStep, cameraStatus, legoBlocks, legoInventory, legoStepIndex]);

  const addEvent = useCallback((label: string, detail: string) => {
    eventCounterRef.current += 1;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${eventCounterRef.current}`;
    setEvents((current) => [{ id, label, detail }, ...current].slice(0, 8));
  }, []);

  const refreshCameraDevices = useCallback(async () => {
    try {
      if (!navigator.mediaDevices?.enumerateDevices) {
        return;
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter((device) => device.kind === "videoinput");
      setCameraDevices(videoDevices);
      setSelectedCameraId((current) => current || videoDevices[0]?.deviceId || "");
    } catch {
      setCameraDevices([]);
    }
  }, []);

  const connectSocket = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState <= WebSocket.OPEN) {
      return socketRef.current;
    }
    const socket = new WebSocket(backendWsUrl());
    socketRef.current = socket;
    setConnectionStatus("Connecting");

    socket.onopen = () => {
      setConnectionStatus("Connected");
      addEvent("WebSocket", "Connected");
    };
    socket.onclose = () => {
      setConnectionStatus("Disconnected");
      addEvent("WebSocket", "Disconnected");
    };
    socket.onerror = () => {
      setConnectionStatus("Error");
      addEvent("WebSocket", "Connection error");
    };
    socket.onmessage = (event) => {
      const envelope = JSON.parse(event.data) as WsEnvelope;
      handleEnvelope(envelope);
    };
    return socket;
  }, [addEvent]);

  const sendSocket = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    socket.send(JSON.stringify({ type, payload }));
    return true;
  }, []);

  const sendWhenOpen = useCallback(
    (type: string, payload: Record<string, unknown> = {}, timeoutMs = 1800) => {
      const socket = connectSocket();
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type, payload }));
        return;
      }
      let timeout = 0;
      const handleOpen = () => {
        window.clearTimeout(timeout);
        socket.send(JSON.stringify({ type, payload }));
      };
      timeout = window.setTimeout(() => {
        socket.removeEventListener("open", handleOpen);
        addEvent("Command", "WebSocket is still connecting");
      }, timeoutMs);
      socket.addEventListener("open", handleOpen, { once: true });
    },
    [addEvent, connectSocket]
  );

  const submitSpokenTranscript = useCallback(
    (spokenText: string, source: "OpenAI" | "Browser") => {
      const text = spokenText.trim();
      if (!text) {
        addEvent("Speech", `${source} transcript was empty`);
        return;
      }
      setTranscript(text);
      setParsedCommand(null);
      setTarget(null);
      setCandidates([]);
      setSessionState("PARSING_COMMAND");
      sendWhenOpen("command.submit", { text });
    },
    [addEvent, sendWhenOpen]
  );

  const handleEnvelope = useCallback(
    (envelope: WsEnvelope) => {
      if (envelope.type === "session.state") {
        const nextState = envelope.payload.state as SessionState;
        setSessionState(nextState);
        addEvent("State", `${envelope.payload.transition ?? nextState}`);
      }
      if (envelope.type === "command.parsed") {
        setParsedCommand(envelope.payload.command as ParsedCommand);
        addEvent("Parsed", (envelope.payload.command as ParsedCommand).object_phrase ?? "unclear");
      }
      if (envelope.type === "detection.candidates") {
        const resolution = envelope.payload.resolution as { candidates: DetectionResult[]; status: string };
        setCandidates(resolution.candidates ?? []);
        addEvent("Detection", `${resolution.status} (${String(envelope.payload.detector_backend ?? "detector")})`);
      }
      if (envelope.type === "target.locked" || envelope.type === "target.updated") {
        const nextTarget = envelope.payload.target as TargetState;
        setTarget(nextTarget);
        setCandidates([]);
        addEvent("Target", `${nextTarget.status} #${nextTarget.tracker_id}`);
      }
      if (envelope.type === "candidate.verified") {
        const verification = envelope.payload.verification as { mode?: string; score?: number; reason?: string };
        addEvent("Verifier", `${verification.mode ?? "context"} ${fmt(Number(verification.score ?? 0) * 100)}%`);
      }
      if (envelope.type === "target.temporarily_lost" || envelope.type === "target.lost") {
        const nextTarget = envelope.payload.target as TargetState;
        setTarget(nextTarget);
        addEvent("Target", nextTarget.status);
      }
      if (envelope.type === "system.metrics") {
        setMetrics(envelope.payload as unknown as Metrics);
      }
      if (envelope.type === "error") {
        addEvent("Error", String(envelope.payload.message ?? "Unknown error"));
      }
    },
    [addEvent]
  );

  const drawOverlay = useCallback(() => {
    const video = videoRef.current;
    const canvas = overlayRef.current;
    if (!video || !canvas) {
      return;
    }
    const rect = video.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, rect.width, rect.height);

    const frame = { width: video.videoWidth || rect.width, height: video.videoHeight || rect.height };
    const display = { width: rect.width, height: rect.height };

    const drawBox = (bbox: BBox, color: string, label: string, dashed: boolean, fillText = "#101314") => {
      const [x1, y1, x2, y2] = frameBBoxToDisplay(bbox, frame, display);
      context.save();
      context.strokeStyle = color;
      context.lineWidth = 3;
      context.setLineDash(dashed ? [8, 6] : []);
      context.strokeRect(x1, y1, x2 - x1, y2 - y1);
      context.setLineDash([]);
      context.fillStyle = color;
      context.font = "600 13px Inter, system-ui, sans-serif";
      const width = Math.max(34, context.measureText(label).width + 12);
      context.fillRect(x1, Math.max(0, y1 - 24), width, 22);
      context.fillStyle = fillText;
      context.fillText(label, x1 + 6, Math.max(15, y1 - 8));
      context.restore();
    };

    const displayPoint = (point: { x: number; y: number }) => {
      const [x, y] = frameBBoxToDisplay([point.x, point.y, point.x, point.y], frame, display);
      return { x, y };
    };

    if (sessionState === "NEEDS_SELECTION" || sessionState === "SEARCHING") {
      candidates.forEach((candidate, index) => {
        drawBox(candidate.bbox, "#f2c94c", `${index + 1}`, true);
      });
    }

    if (target) {
      const color = target.status === "LOST" ? "#f25555" : target.status === "TEMPORARILY_LOST" ? "#f2994a" : "#2ec46d";
      drawBox(target.bbox, color, `#${target.tracker_id}`, target.status !== "TRACKING" && target.status !== "LOCKED");
    }

    const colorMap: Record<string, string> = {
      black: "#2d3134",
      red: "#f25555",
      blue: "#34aee8",
      yellow: "#f2c94c"
    };

    legoBlocks.forEach((block) => {
      const isSource = legoSteps.some((step) => step.sourceColor === block.color);
      const isDestination = legoSteps.some((step) => step.targetColor === block.color);
      const stroke = isSource ? "#2ec46d" : isDestination ? "#f2c94c" : colorMap[block.color];
      drawBox(
        block.bbox,
        stroke,
        block.color,
        !isSource && !isDestination,
        block.color === "black" ? "#ffffff" : "#101314"
      );
    });

    const drawArrow = (source: LegoBlock, destination: LegoBlock, stepNumber: number) => {
      const from = displayPoint(source.center);
      const to = displayPoint(destination.center);
      context.save();
      context.strokeStyle = "#2ec46d";
      context.fillStyle = "#2ec46d";
      context.lineWidth = 4;
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
      const angle = Math.atan2(to.y - from.y, to.x - from.x);
      context.beginPath();
      context.moveTo(to.x, to.y);
      context.lineTo(to.x - 18 * Math.cos(angle - 0.45), to.y - 18 * Math.sin(angle - 0.45));
      context.lineTo(to.x - 18 * Math.cos(angle + 0.45), to.y - 18 * Math.sin(angle + 0.45));
      context.closePath();
      context.fill();
      const labelX = from.x + (to.x - from.x) * 0.5;
      const labelY = from.y + (to.y - from.y) * 0.5;
      context.fillStyle = "#101314";
      context.strokeStyle = "#ffffff";
      context.lineWidth = 2;
      context.beginPath();
      context.arc(labelX, labelY, 14, 0, Math.PI * 2);
      context.fillStyle = "#2ec46d";
      context.fill();
      context.stroke();
      context.fillStyle = "#ffffff";
      context.font = "800 14px Inter, system-ui, sans-serif";
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText(String(stepNumber), labelX, labelY);
      context.restore();
    };

    legoSteps.forEach((step, index) => {
      const source = pickBlockByColor(legoBlocks, step.sourceColor);
      const destination = pickBlockByColor(legoBlocks, step.targetColor);
      if (source && destination) {
        drawArrow(source, destination, index + 1);
      }
    });
  }, [candidates, legoBlocks, legoSteps, sessionState, target]);

  useEffect(() => {
    drawOverlay();
  }, [drawOverlay]);

  useEffect(() => {
    const onResize = () => drawOverlay();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [drawOverlay]);

  useEffect(() => {
    fetch(`${backendHttpUrl()}/api/health`)
      .then((response) => response.json())
      .then((data: { openai_configured?: boolean }) => {
        setOpenAiConfigured(Boolean(data.openai_configured));
        addEvent("Speech", data.openai_configured ? "OpenAI transcription ready" : "Browser speech fallback active");
      })
      .catch(() => {
        setOpenAiConfigured(false);
        addEvent("Speech", "Browser speech fallback active");
      });
  }, [addEvent]);

  useEffect(() => {
    void refreshCameraDevices();
    const handleDeviceChange = () => void refreshCameraDevices();
    navigator.mediaDevices?.addEventListener?.("devicechange", handleDeviceChange);
    return () => {
      navigator.mediaDevices?.removeEventListener?.("devicechange", handleDeviceChange);
    };
  }, [refreshCameraDevices]);

  const sendFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = captureRef.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return;
    }
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) {
      return;
    }
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.drawImage(video, 0, 0, width, height);
    const image = canvas.toDataURL("image/jpeg", 0.72);
    sendSocket("frame.jpeg", { image, width, height, client_ts: new Date().toISOString() });
  }, [sendSocket]);

  const scanLegoBlocks = useCallback(async () => {
    const video = videoRef.current;
    const canvas = captureRef.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || !video.videoWidth || !video.videoHeight) {
      setLegoStatus("Camera not ready");
      return;
    }
    const maxWidth = 960;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    const width = Math.max(1, Math.round(video.videoWidth * scale));
    const height = Math.max(1, Math.round(video.videoHeight * scale));
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
      setLegoStatus("Canvas unavailable");
      return;
    }
    context.drawImage(video, 0, 0, width, height);
    const localCandidates = detectLegoBlocksFromImage(context.getImageData(0, 0, width, height));
    if (!localCandidates.length) {
      legoVerificationRef.current.signature = "";
      setLegoBlocks([]);
      return;
    }
    if (openAiConfigured === null) {
      setLegoStatus("Checking OpenAI verifier");
      return;
    }

    const signature = localCandidates
      .map((block) => `${block.color}:${block.bbox.map((value) => Math.round(value / 12)).join(",")}`)
      .join("|");
    const now = performance.now();
    if (
      legoVerificationRef.current.inFlight ||
      (legoVerificationRef.current.signature === signature && now - legoVerificationRef.current.verifiedAt < 3200)
    ) {
      return;
    }

    const originalScaleCandidates = localCandidates.map((block) => ({
      ...block,
      bbox: block.bbox.map((value) => value / scale) as BBox,
      center: { x: block.center.x / scale, y: block.center.y / scale }
    }));
    legoVerificationRef.current = { signature, verifiedAt: now, inFlight: true };
    setLegoStatus("Verifying color blocks");
    try {
      if (openAiConfigured) {
        const response = await fetch(`${backendHttpUrl()}/api/lego/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image: canvas.toDataURL("image/jpeg", 0.78),
            width,
            height,
            candidates: localCandidates.map((block) => ({
              id: block.id,
              color: block.color,
              bbox: block.bbox,
              confidence: block.confidence
            }))
          })
        });
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const verification = (await response.json()) as LegoVerificationResponse;
        setLegoVerifierMode(verification.mode);
        const verifiedColors = new Set(verification.verified_colors);
        const verifiedBlocks = originalScaleCandidates
          .filter((block) => verifiedColors.has(block.color))
          .map((block) => ({ ...block, verified: true }));
        setLegoBlocks(verifiedBlocks);
        setDetectedProduct(identifyProduct(verifiedBlocks));
      } else {
        setLegoVerifierMode("local-fallback");
        const localBlocks = originalScaleCandidates.map((block) => ({ ...block, verified: false }));
        setLegoBlocks(localBlocks);
        setDetectedProduct(identifyProduct(localBlocks));
      }
    } catch (error) {
      setLegoVerifierMode("verify-error");
      setLegoBlocks([]);
      addEvent("Lego", error instanceof Error ? error.message : "Verification failed");
    } finally {
      legoVerificationRef.current.inFlight = false;
      legoVerificationRef.current.verifiedAt = performance.now();
    }
  }, [addEvent, openAiConfigured]);

  const startCamera = async (deviceId = selectedCameraId) => {
    connectSocket();
    try {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      const videoConstraint: MediaTrackConstraints = deviceId
        ? { deviceId: { exact: deviceId } }
        : { facingMode: "environment" };
      const stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraStatus("Live");
      const activeDeviceId = stream.getVideoTracks()[0]?.getSettings().deviceId;
      if (activeDeviceId) {
        setSelectedCameraId(activeDeviceId);
      }
      void refreshCameraDevices();
      addEvent("Camera", "Live");
      if (frameTimerRef.current) {
        window.clearInterval(frameTimerRef.current);
      }
      frameTimerRef.current = window.setInterval(sendFrame, 350);
      window.setTimeout(drawOverlay, 100);
      window.setTimeout(() => void scanLegoBlocks(), 180);
    } catch (error) {
      setCameraStatus("Denied");
      addEvent("Camera", error instanceof Error ? error.message : "Permission denied");
    }
  };

  const handleCameraDeviceChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextDeviceId = event.target.value;
    setSelectedCameraId(nextDeviceId);
    if (cameraStatus === "Live") {
      void startCamera(nextDeviceId);
    }
  };

  const stopTracking = () => {
    sendWhenOpen("tracking.stop");
    setSessionState("STOPPED");
    setTarget(null);
    setCandidates([]);
  };

  useEffect(() => {
    if (cameraStatus !== "Live") {
      if (legoTimerRef.current) {
        window.clearInterval(legoTimerRef.current);
        legoTimerRef.current = null;
      }
      return;
    }
    void scanLegoBlocks();
    legoTimerRef.current = window.setInterval(() => void scanLegoBlocks(), 900);
    return () => {
      if (legoTimerRef.current) {
        window.clearInterval(legoTimerRef.current);
        legoTimerRef.current = null;
      }
    };
  }, [cameraStatus, scanLegoBlocks]);

  useEffect(() => {
    drawOverlay();
  }, [drawOverlay, legoStepIndex, legoStepsText]);

  useEffect(() => {
    if (cameraStatus !== "Live") {
      setLegoStatus("Start camera to identify color blocks");
    } else if (!legoBlocks.length) {
      setLegoStatus("Identifying color blocks");
    } else {
      setLegoStatus(`Verified (${legoVerifierMode}): ${legoInventory}`);
    }
  }, [cameraStatus, legoBlocks.length, legoInventory, legoVerifierMode]);

  const startBrowserSpeechRecognition = () => {
    const SpeechRecognitionCtor =
      (window as unknown as { SpeechRecognition?: new () => BrowserSpeechRecognition }).SpeechRecognition ??
      (window as unknown as { webkitSpeechRecognition?: new () => BrowserSpeechRecognition }).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      addEvent("Speech", "Browser speech recognition unavailable");
      return false;
    }

    const recognition = new SpeechRecognitionCtor();
    browserSpeechTranscriptRef.current = "";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interimText += result[0].transcript;
        }
      }
      const combined = `${finalText} ${interimText}`.trim();
      if (combined) {
        browserSpeechTranscriptRef.current = combined;
        setTranscript(combined);
      }
    };
    recognition.onerror = (event) => {
      addEvent("Speech", event.error ? `Browser speech: ${event.error}` : "Browser speech failed");
      setIsRecording(false);
    };
    recognition.onend = () => {
      const spokenText = browserSpeechTranscriptRef.current;
      setIsRecording(false);
      submitSpokenTranscript(spokenText, "Browser");
    };
    speechRecognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
    addEvent("Speech", "Browser listening");
    return true;
  };

  const startRecording = async () => {
    if (openAiConfigured === false && startBrowserSpeechRecognition()) {
      return;
    }

    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(audioStream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        audioStream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", blob, "command.webm");
        const started = performance.now();
        try {
          const response = await fetch(`${backendHttpUrl()}/api/transcribe`, { method: "POST", body: formData });
          if (!response.ok) {
            throw new Error(await response.text());
          }
          const data = (await response.json()) as { transcription: { transcript: string }; latency_ms: number };
          setMetrics((current) => ({ ...current, speech_transcription_latency_ms: data.latency_ms || performance.now() - started }));
          submitSpokenTranscript(data.transcription.transcript, "OpenAI");
        } catch (error) {
          if (startBrowserSpeechRecognition()) {
            addEvent("Speech", "OpenAI unavailable; using browser speech");
          } else {
            addEvent("Speech", error instanceof Error ? error.message : "Transcription failed");
          }
        } finally {
          setIsRecording(false);
        }
      };
      recorder.start();
      setIsRecording(true);
      addEvent("Speech", "Recording");
    } catch (error) {
      addEvent("Speech", error instanceof Error ? error.message : "Microphone unavailable");
    }
  };

  const stopRecording = () => {
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      speechRecognitionRef.current = null;
      return;
    }
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  };

  useEffect(() => {
    const isEditableTarget = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName.toLowerCase();
      return tag === "input" || tag === "textarea" || target.isContentEditable;
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code !== "Space" || event.repeat || isEditableTarget(event.target)) {
        return;
      }
      event.preventDefault();
      void startRecording();
    };
    const onKeyUp = (event: KeyboardEvent) => {
      if (event.code !== "Space" || isEditableTarget(event.target)) {
        return;
      }
      event.preventDefault();
      stopRecording();
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  });

  const handleOverlayClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (sessionState !== "NEEDS_SELECTION") {
      return;
    }
    const video = videoRef.current;
    const canvas = overlayRef.current;
    if (!video || !canvas) {
      return;
    }
    const rect = canvas.getBoundingClientRect();
    sendSocket("candidate.select", {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      display_width: rect.width,
      display_height: rect.height,
      frame_width: video.videoWidth,
      frame_height: video.videoHeight
    });
  };

  useEffect(() => {
    return () => {
      if (frameTimerRef.current) {
        window.clearInterval(frameTimerRef.current);
      }
      if (legoTimerRef.current) {
        window.clearInterval(legoTimerRef.current);
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      socketRef.current?.close();
    };
  }, []);

  const trackingLabel = target?.label ?? parsedCommand?.object_phrase ?? "None";

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Activity size={20} aria-hidden="true" />
          </div>
          <div>
            <h1>ActionShare</h1>
            <span>Teaching Mode</span>
          </div>
        </div>
        <div className="status-strip" aria-label="System status">
          <StatusPill icon={<Camera size={16} />} label={cameraStatus} tone={cameraStatus === "Live" ? "good" : "neutral"} />
          <StatusPill
            icon={connectionStatus === "Connected" ? <Wifi size={16} /> : <WifiOff size={16} />}
            label={connectionStatus}
            tone={connectionStatus === "Connected" ? "good" : connectionStatus === "Error" ? "bad" : "neutral"}
          />
          <StatusPill icon={<Activity size={16} />} label={`${fmt(metrics.video_fps)} FPS`} tone="neutral" />
          <StatusPill icon={<CheckCircle2 size={16} />} label={`${fmt(metrics.tracking_update_latency_ms, 1)} ms`} tone="neutral" />
          <button className="nav-button" onClick={onSwitchMode} title="Go to Skill Manager">
            <BarChart3 size={16} />
            <span>Skill Manager</span>
          </button>
        </div>
      </header>

      <main className="workspace">
        <section className="camera-column" aria-label="Live camera">
          <div className="video-stage">
            <video ref={videoRef} muted playsInline />
            <canvas
              ref={overlayRef}
              className={sessionState === "NEEDS_SELECTION" ? "overlay selectable" : "overlay"}
              onClick={handleOverlayClick}
              aria-label="Object selection overlay"
            />
            <canvas ref={captureRef} hidden />
            <div className={`tracking-banner state-${sessionState.toLowerCase()}`}>
              <span>{selectedProduct ? `Building: ${selectedProduct === "product-1" ? "Product 1 (Blue on Black)" : "Product 2 (Black on Blue)"}` : "Select a product below"}</span>
              <strong style={{ color: detectedProduct && selectedProduct && detectedProduct.id === selectedProduct ? "#2ec46d" : undefined }}>
                {detectedProduct ? `DETECTED: ${detectedProduct.name}` : legoStatus}
              </strong>
            </div>
          </div>

          <div className="control-bar">
            <button className="icon-button primary" type="button" onClick={() => void startCamera()} title="Start camera">
              <Play size={18} />
              <span>Start camera</span>
            </button>
            <label className="camera-select">
              <Camera size={17} aria-hidden="true" />
              <select aria-label="Camera device" value={selectedCameraId} onChange={handleCameraDeviceChange}>
                {cameraDevices.length === 0 ? (
                  <option value="">Default camera</option>
                ) : (
                  cameraDevices.map((device, index) => (
                    <option key={device.deviceId || `camera-${index}`} value={device.deviceId}>
                      {device.label || `Camera ${index + 1}`}
                    </option>
                  ))
                )}
              </select>
            </label>
            <button
              className={isRecording ? "icon-button danger active" : "icon-button"}
              type="button"
              onPointerDown={() => void startRecording()}
              onPointerUp={stopRecording}
              onPointerLeave={stopRecording}
              title="Hold to speak"
            >
              <Mic size={18} />
              <span>{isRecording ? "Recording" : "Hold to speak"}</span>
            </button>
            <button className="icon-button stop" type="button" onClick={stopTracking} title="Stop tracking">
              <Square size={17} />
              <span>Stop</span>
            </button>
          </div>

          <div className="lego-panel" aria-label="Lego AR instructions">
            <div className="lego-progress">
              <strong style={{ fontSize: "1.1em" }}>Select Product to Build:</strong>
              <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setSelectedProduct("product-1")}
                  style={{
                    padding: "12px 20px",
                    fontSize: "1em",
                    fontWeight: 600,
                    border: "2px solid",
                    borderColor: selectedProduct === "product-1" ? "#2ec46d" : "#444",
                    borderRadius: "8px",
                    background: selectedProduct === "product-1" ? "#2ec46d" : "#1a1d1f",
                    color: selectedProduct === "product-1" ? "#000" : "#fff",
                    cursor: "pointer"
                  }}
                >
                  Product 1: Blue on Black
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedProduct("product-2")}
                  style={{
                    padding: "12px 20px",
                    fontSize: "1em",
                    fontWeight: 600,
                    border: "2px solid",
                    borderColor: selectedProduct === "product-2" ? "#2ec46d" : "#444",
                    borderRadius: "8px",
                    background: selectedProduct === "product-2" ? "#2ec46d" : "#1a1d1f",
                    color: selectedProduct === "product-2" ? "#000" : "#fff",
                    cursor: "pointer"
                  }}
                >
                  Product 2: Black on Blue
                </button>
              </div>
            </div>
            <div className="lego-progress" style={{ marginTop: "12px" }}>
              <span>Detected colors: {legoInventory || "none"}</span>
              {detectedProduct && selectedProduct && (
                <strong style={{ 
                  fontSize: "1.3em", 
                  color: detectedProduct.id === selectedProduct ? "#2ec46d" : "#f25555",
                  marginTop: "8px",
                  display: "block"
                }}>
                  {detectedProduct.id === selectedProduct ? "CORRECT!" : `Wrong - Detected ${detectedProduct.name}`}
                </strong>
              )}
            </div>
          </div>
        </section>

        <aside className="side-panel" aria-label="Session details">
          <PanelRow label="Transcript" value={transcript || "-"} />
          <PanelRow label="Parsed object" value={parsedCommand?.object_phrase ?? "-"} />
          <PanelRow label="Current state" value={sessionState} />
          <PanelRow label="Target track ID" value={target ? String(target.tracker_id) : "-"} />
          <PanelRow label="Confidence" value={target ? `${fmt(target.confidence * 100)}%` : "-"} />

          <div className="metric-grid">
            <Metric label="YOLOE" value={`${fmt(metrics.yoloe_inference_latency_ms, 1)} ms`} />
            <Metric label="Context" value={`${fmt(metrics.context_verification_latency_ms, 1)} ms`} />
            <Metric label="Parse" value={`${fmt(metrics.command_parsing_latency_ms, 1)} ms`} />
            <Metric label="First box" value={`${fmt(metrics.transcript_to_first_detection_ms, 1)} ms`} />
            <Metric label="Lost" value={String(metrics.lost_and_reacquired_count)} />
          </div>

          <div className="events">
            <div className="events-title">
              <MousePointer2 size={16} />
              <span>Recent system events</span>
            </div>
            {events.map((item) => (
              <div className="event-line" key={item.id}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
          </div>
        </aside>
      </main>
    </div>
  );
}

function StatusPill({ icon, label, tone }: { icon: React.ReactNode; label: string; tone: "good" | "bad" | "neutral" }) {
  return (
    <div className={`status-pill ${tone}`}>
      {icon}
      <span>{label}</span>
    </div>
  );
}

function PanelRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SkillManagerWithNav({ onSwitchMode }: { onSwitchMode: () => void }) {
  return (
    <div className="skill-manager-wrapper">
      <header className="sm-top-nav">
        <button className="nav-back-button" onClick={onSwitchMode} title="Back to Teaching Mode">
          <Activity size={16} />
          <span>Back to Teaching Mode</span>
        </button>
      </header>
      <SkillManager />
    </div>
  );
}
