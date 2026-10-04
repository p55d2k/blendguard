import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "../page";

describe("home page", () => {
  it("renders the product name and positioning", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "BlendGuard" })).toBeInTheDocument();
    expect(screen.getByText(/diversified ETF portfolio/i)).toBeInTheDocument();
  });

  it("does not render an allocation without an explanation", () => {
    const { container } = render(<Home />);
    expect(container.textContent ?? "").not.toMatch(/\d+(\.\d+)?%/);
  });
});
