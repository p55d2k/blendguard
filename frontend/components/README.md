# Components

PRESENTATION components only.

- No finance logic. No covariance matrices, `tau`, or solver references.
- Prefer server components; add `"use client"` only when interactivity requires
  it.
- Any component that renders a weight must also render its explanation.
