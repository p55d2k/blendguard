import { describe, expect, it } from "vitest";

import {
  CONFIDENCE_LABELS,
  GOAL_LABELS,
  RISK_LABELS,
  SENTIMENT_LABELS,
  type Confidence,
  type Goal,
  type RiskLevel,
  type Sentiment,
} from "../vocabulary";

describe("consumer vocabulary", () => {
  it("labels every goal, risk level, sentiment and confidence", () => {
    const goals: Goal[] = ["preserve", "balanced", "growth"];
    const risks: RiskLevel[] = ["lower", "medium", "higher"];
    const sentiments: Sentiment[] = ["bearish", "neutral", "bullish"];
    const confidences: Confidence[] = ["low", "medium", "high"];

    for (const g of goals) expect(GOAL_LABELS[g], `goal "${g}"`).toBeTruthy();
    for (const r of risks) expect(RISK_LABELS[r], `risk "${r}"`).toBeTruthy();
    for (const s of sentiments) expect(SENTIMENT_LABELS[s], `sentiment "${s}"`).toBeTruthy();
    for (const c of confidences) expect(CONFIDENCE_LABELS[c], `confidence "${c}"`).toBeTruthy();
  });

  // CONTEXT.md §2: the consumer must never be shown quant jargon.
  it("never leaks quantitative-finance jargon into user-facing labels", () => {
    const jargon = [
      "covariance",
      "tau",
      "omega",
      "black-litterman",
      "black litterman",
      "risk aversion",
      "risk-aversion",
      "posterior",
      "prior",
      "efficient frontier",
      "solver",
      "cvxpy",
      "regression",
      "standard deviation",
      "volatility",
      "correlation",
    ];
    const labels = [
      ...Object.values(GOAL_LABELS),
      ...Object.values(RISK_LABELS),
      ...Object.values(SENTIMENT_LABELS),
      ...Object.values(CONFIDENCE_LABELS),
    ].join(" | ");

    for (const term of jargon) {
      expect(labels.toLowerCase(), `label exposes "${term}"`).not.toContain(term);
    }
  });

  it("keeps every label human-readable", () => {
    for (const label of Object.values(GOAL_LABELS)) {
      expect(label.trim()).toBe(label);
      expect(label.length).toBeGreaterThan(0);
    }
  });
});
