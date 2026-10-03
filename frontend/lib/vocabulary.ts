/** Consumer-facing vocabulary. No covariance matrices, tau, or solvers. */

export type Goal = "preserve" | "balanced" | "growth";
export type RiskLevel = "lower" | "medium" | "higher";
export type Sentiment = "bearish" | "neutral" | "bullish";
export type Confidence = "low" | "medium" | "high";
export type Preset = "conservative" | "balanced" | "growth";

export const GOAL_LABELS: Record<Goal, string> = {
  preserve: "Preserve wealth",
  balanced: "Balanced growth",
  growth: "Long-term growth",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  lower: "Lower",
  medium: "Medium",
  higher: "Higher",
};

export const SENTIMENT_LABELS: Record<Sentiment, string> = {
  bearish: "Bearish",
  neutral: "Neutral",
  bullish: "Bullish",
};

export const CONFIDENCE_LABELS: Record<Confidence, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};
