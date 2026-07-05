import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  clearRect: vi.fn(),
  drawImage: vi.fn(),
  fillRect: vi.fn(),
  fillText: vi.fn(),
  measureText: vi.fn(() => ({ width: 40 })),
  restore: vi.fn(),
  save: vi.fn(),
  scale: vi.fn(),
  setLineDash: vi.fn(),
  setTransform: vi.fn(),
  strokeRect: vi.fn()
})) as unknown as HTMLCanvasElement["getContext"];

HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/jpeg;base64,") as unknown as HTMLCanvasElement["toDataURL"];
