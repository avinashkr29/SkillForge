import { describe, expect, it } from "vitest";
import { displayPointToFrame, frameBBoxToDisplay } from "./geometry";

describe("geometry", () => {
  it("converts display click coordinates to original frame coordinates", () => {
    expect(displayPointToFrame({ x: 160, y: 90 }, { width: 320, height: 180 }, { width: 640, height: 360 })).toEqual({
      x: 320,
      y: 180
    });
  });

  it("converts frame boxes to display boxes", () => {
    expect(frameBBoxToDisplay([100, 50, 300, 150], { width: 400, height: 200 }, { width: 200, height: 100 })).toEqual([
      50,
      25,
      150,
      75
    ]);
  });
});
