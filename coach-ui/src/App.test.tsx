import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App (Step 1 smoke test)", () => {
  it("renders the product title", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /Customer Service AI Coach/i,
    );
  });

  it("identifies itself as the v0 scaffold", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/v0/);
  });
});
