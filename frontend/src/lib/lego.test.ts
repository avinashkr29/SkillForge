import { describe, expect, it } from "vitest";
import { classifyLegoPixel, detectLegoBlocksFromImage, parseLegoSteps } from "./lego";

function solidImage(width: number, height: number, rectangles: Array<{ x: number; y: number; w: number; h: number; rgb: [number, number, number] }>) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let offset = 0; offset < data.length; offset += 4) {
    data[offset] = 160;
    data[offset + 1] = 160;
    data[offset + 2] = 150;
    data[offset + 3] = 255;
  }
  rectangles.forEach((rect) => {
    for (let y = rect.y; y < rect.y + rect.h; y += 1) {
      for (let x = rect.x; x < rect.x + rect.w; x += 1) {
        const offset = (y * width + x) * 4;
        data[offset] = rect.rgb[0];
        data[offset + 1] = rect.rgb[1];
        data[offset + 2] = rect.rgb[2];
        data[offset + 3] = 255;
      }
    }
  });
  return { data, width, height };
}

describe("lego AR helpers", () => {
  it("parses source and target colors from an assembly step", () => {
    const [step] = parseLegoSteps("First take the white block and put it on the black block");

    expect(step.sourceColor).toBe("white");
    expect(step.targetColor).toBe("black");
  });

  it("infers chained top placement from the previous placed block", () => {
    const steps = parseLegoSteps(
      ["Take the white block and put it on the black block.", "Take the red block and put it on top.", "Take the blue block and put it on top."].join("\n")
    );

    expect(steps.map((step) => [step.sourceColor, step.targetColor])).toEqual([
      ["white", "black"],
      ["red", "white"],
      ["blue", "red"]
    ]);
  });

  it("classifies the primary Lego demo colors", () => {
    expect(classifyLegoPixel(30, 30, 32)).toBe("black");
    expect(classifyLegoPixel(242, 242, 235)).toBe("white");
    expect(classifyLegoPixel(226, 18, 76)).toBe("red");
    expect(classifyLegoPixel(30, 170, 230)).toBe("blue");
    expect(classifyLegoPixel(235, 200, 36)).toBe("yellow");
  });

  it("detects one separate block region per color", () => {
    const image = solidImage(220, 120, [
      { x: 12, y: 20, w: 24, h: 84, rgb: [28, 29, 31] },
      { x: 70, y: 18, w: 26, h: 86, rgb: [245, 245, 238] },
      { x: 128, y: 16, w: 28, h: 88, rgb: [224, 20, 78] },
      { x: 178, y: 30, w: 30, h: 52, rgb: [32, 165, 230] }
    ]);

    const blocks = detectLegoBlocksFromImage(image, { minArea: 200, maxAreaRatio: 0.2 });

    expect(blocks.map((block) => block.color).sort()).toEqual(["black", "blue", "red", "white"]);
    expect(new Set(blocks.map((block) => block.color)).size).toBe(blocks.length);
  });
});
