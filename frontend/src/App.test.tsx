import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders teaching mode controls", () => {
    render(<App />);

    expect(screen.getByText("ActionShare")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start camera/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Camera device")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /hold to speak/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Lego assembly steps")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /detect blocks/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /load steps/i })).not.toBeInTheDocument();
  });
});
