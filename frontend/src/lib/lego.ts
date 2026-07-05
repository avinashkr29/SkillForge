import type { BBox } from "./geometry";

export type LegoColor = "black" | "red" | "blue" | "yellow";

export type LegoBlock = {
  id: string;
  color: LegoColor;
  bbox: BBox;
  center: { x: number; y: number };
  area: number;
  confidence: number;
  verified?: boolean;
};

export type LegoAssemblyStep = {
  id: string;
  text: string;
  sourceColor: LegoColor | null;
  targetColor: LegoColor | null;
};

const legoColors: LegoColor[] = ["black", "red", "blue", "yellow"];

export const defaultLegoSteps = [
  "Product 1: Put blue block on top of black block.",
  "Product 2: Put black block on top of blue block.",
].join("\n");

export type Product = {
  id: string;
  name: string;
  topColor: LegoColor;
  bottomColor: LegoColor;
};

export const products: Product[] = [
  { id: "product-1", name: "Product 1", topColor: "blue", bottomColor: "black" },
  { id: "product-2", name: "Product 2", topColor: "black", bottomColor: "blue" },
];

function rgbToHsv(r: number, g: number, b: number) {
  const nr = r / 255;
  const ng = g / 255;
  const nb = b / 255;
  const max = Math.max(nr, ng, nb);
  const min = Math.min(nr, ng, nb);
  const delta = max - min;
  let h = 0;

  if (delta !== 0) {
    if (max === nr) {
      h = ((ng - nb) / delta) % 6;
    } else if (max === ng) {
      h = (nb - nr) / delta + 2;
    } else {
      h = (nr - ng) / delta + 4;
    }
    h *= 60;
    if (h < 0) {
      h += 360;
    }
  }

  return { h, s: max === 0 ? 0 : delta / max, v: max };
}

export function classifyLegoPixel(r: number, g: number, b: number): LegoColor | null {
  const { h, s, v } = rgbToHsv(r, g, b);

  // Skip white/bright areas (tissue paper background)
  if (v > 0.74 && s < 0.24) {
    return null;
  }
  if (v < 0.28) {
    return "black";
  }
  if (r > 130 && s > 0.38 && (h >= 330 || h <= 18 || (h >= 315 && b > g))) {
    return "red";
  }
  if (b > 120 && g > 70 && r < 120 && h >= 175 && h <= 230 && s > 0.32) {
    return "blue";
  }
  if (r > 140 && g > 110 && b < 115 && h >= 32 && h <= 68 && s > 0.35) {
    return "yellow";
  }
  return null;
}

export function parseLegoSteps(text: string): LegoAssemblyStep[] {
  let previousPlacedColor: LegoColor | null = null;
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const lower = line.toLowerCase();
      const colors = legoColors
        .map((color) => ({ color, position: lower.indexOf(color) }))
        .filter((match) => match.position >= 0)
        .sort((a, b) => a.position - b.position)
        .map((match) => match.color);
      const sourceColor = colors[0] ?? null;
      let targetColor: LegoColor | null = colors[1] ?? null;
      const placementMatch = lower.match(
        /(black|red|blue|yellow)\s+(?:block|brick)?.*?(?:on|onto|over|above|top of)\s+(?:the\s+)?(black|red|blue|yellow)/
      );
      if (placementMatch) {
        targetColor = placementMatch[2] as LegoColor;
      } else if (sourceColor && /(on top|top|above|onto|on it|again)/.test(lower)) {
        targetColor = previousPlacedColor;
      }
      if (sourceColor) {
        previousPlacedColor = sourceColor;
      }
      return {
        id: `step-${index + 1}`,
        text: line,
        sourceColor,
        targetColor
      };
    });
}

export function detectLegoBlocksFromImage(
  imageData: Pick<ImageData, "data" | "width" | "height">,
  options: { minArea?: number; maxAreaRatio?: number } = {}
): LegoBlock[] {
  const { data, width, height } = imageData;
  const minArea = options.minArea ?? Math.max(140, Math.round(width * height * 0.0018));
  const maxArea = width * height * (options.maxAreaRatio ?? 0.065);
  const labels = new Int8Array(width * height);
  const visited = new Uint8Array(width * height);

  for (let pixel = 0; pixel < width * height; pixel += 1) {
    const offset = pixel * 4;
    const color = classifyLegoPixel(data[offset], data[offset + 1], data[offset + 2]);
    labels[pixel] = color ? legoColors.indexOf(color) + 1 : 0;
  }

  const blocks: LegoBlock[] = [];
  const queue = new Int32Array(width * height);

  for (let start = 0; start < labels.length; start += 1) {
    const label = labels[start];
    if (label === 0 || visited[start]) {
      continue;
    }

    let head = 0;
    let tail = 0;
    let area = 0;
    let minX = width;
    let minY = height;
    let maxX = 0;
    let maxY = 0;
    queue[tail] = start;
    tail += 1;
    visited[start] = 1;

    while (head < tail) {
      const current = queue[head];
      head += 1;
      const x = current % width;
      const y = Math.floor(current / width);
      area += 1;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);

      const neighbors = [current - 1, current + 1, current - width, current + width];
      for (const next of neighbors) {
        if (next < 0 || next >= labels.length || visited[next] || labels[next] !== label) {
          continue;
        }
        const nextX = next % width;
        if (Math.abs(nextX - x) > 1) {
          continue;
        }
        visited[next] = 1;
        queue[tail] = next;
        tail += 1;
      }
    }

    const boxWidth = maxX - minX + 1;
    const boxHeight = maxY - minY + 1;
    const boxArea = boxWidth * boxHeight;
    const fillRatio = area / Math.max(1, boxArea);
    const longestSide = Math.max(boxWidth, boxHeight);
    const shortestSide = Math.max(1, Math.min(boxWidth, boxHeight));
    const aspect = longestSide / shortestSide;
    const touchesFrame = minX <= 2 || minY <= 2 || maxX >= width - 3 || maxY >= height - 3;

    if (
      area < minArea ||
      area > maxArea ||
      boxArea < minArea * 1.2 ||
      fillRatio < 0.28 ||
      aspect < 1.1 ||
      aspect > 5.4 ||
      touchesFrame
    ) {
      continue;
    }

    const color = legoColors[label - 1];
    blocks.push({
      id: `${color}-${Math.round(minX)}-${Math.round(minY)}`,
      color,
      bbox: [minX, minY, maxX, maxY],
      center: { x: (minX + maxX) / 2, y: (minY + maxY) / 2 },
      area,
      confidence: Math.min(0.99, Math.max(0.45, fillRatio + Math.min(0.3, area / maxArea)))
    });
  }

  const saturatedBlocks = blocks.filter((block) => block.color === "red" || block.color === "blue" || block.color === "yellow");
  const referenceArea =
    saturatedBlocks.length > 0
      ? saturatedBlocks.map((block) => block.area).sort((a, b) => a - b)[Math.floor(saturatedBlocks.length / 2)]
      : null;

  const filteredBlocks = blocks.filter((block) => {
    if (block.color !== "black") {
      return true;
    }
    if (referenceArea === null) {
      return block.confidence >= 0.72;
    }
    return block.area >= referenceArea * 0.35 && block.area <= referenceArea * 2.8;
  });

  const bestByColor = new Map<LegoColor, LegoBlock>();
  filteredBlocks
    .sort((a, b) => b.confidence - a.confidence || b.area - a.area)
    .forEach((block) => {
      if (!bestByColor.has(block.color)) {
        bestByColor.set(block.color, block);
      }
    });

  return Array.from(bestByColor.values()).sort((a, b) => a.center.x - b.center.x);
}

export function pickBlockByColor(blocks: LegoBlock[], color: LegoColor | null): LegoBlock | null {
  if (!color) {
    return null;
  }
  return blocks.filter((block) => block.color === color).sort((a, b) => b.area - a.area)[0] ?? null;
}

export function identifyProduct(blocks: LegoBlock[]): Product | null {
  const blue = pickBlockByColor(blocks, "blue");
  const black = pickBlockByColor(blocks, "black");
  
  if (!blue || !black) {
    return null;
  }
  
  // Check if blocks are stacked (overlapping bounding boxes)
  const overlap = !(blue.bbox[2] < black.bbox[0] || blue.bbox[0] > black.bbox[2] ||
                    blue.bbox[3] < black.bbox[1] || blue.bbox[1] > black.bbox[3]);
  
  if (!overlap) {
    return null;
  }
  
  // The block on top has larger visible area (more prominent in top-down view)
  if (blue.area > black.area) {
    return products[0]; // Product 1: Blue on top of Black
  } else {
    return products[1]; // Product 2: Black on top of Blue
  }
}
