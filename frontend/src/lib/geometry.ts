export type Size = {
  width: number;
  height: number;
};

export type Point = {
  x: number;
  y: number;
};

export type BBox = [number, number, number, number];

export function displayPointToFrame(point: Point, display: Size, frame: Size): Point {
  if (display.width <= 0 || display.height <= 0) {
    throw new Error("display dimensions must be positive");
  }
  return {
    x: (point.x * frame.width) / display.width,
    y: (point.y * frame.height) / display.height
  };
}

export function frameBBoxToDisplay(bbox: BBox, frame: Size, display: Size): BBox {
  if (frame.width <= 0 || frame.height <= 0) {
    throw new Error("frame dimensions must be positive");
  }
  const xScale = display.width / frame.width;
  const yScale = display.height / frame.height;
  return [bbox[0] * xScale, bbox[1] * yScale, bbox[2] * xScale, bbox[3] * yScale];
}
