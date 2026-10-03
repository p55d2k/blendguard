# BlendGuard Frontend

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind 4 · Recharts 3.

PRESENTATION layer only. No finance logic, no covariance matrices, no solver
knowledge in this app.

## Setup

```bash
npm install
npm run dev        # http://localhost:3000
```

Point it at the backend with `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | dev server |
| `npm run build` | production build |
| `npm run start` | serve the production build |
| `npm run lint` | eslint (`next/core-web-vitals` + `next/typescript`) |
| `npm run typecheck` | `tsc --noEmit` |

## Layout

```
app/          routes, layout, global styles
components/   presentational components
lib/          API client, consumer-facing vocabulary
public/       static assets
```

## Rules

- Speak the user's language: growth vs stability, risk tolerance, market views,
  confidence. Covariance matrices, `tau`, and solver concepts belong behind
  optional "How this works" panels, never in the primary flow.
- Every allocation rendered must include its explanation.
- No guaranteed-return or market-prediction language.

## Known audit warnings

`npm audit` reports `braces` / `micromatch` / `fast-glob` high-severity
advisories. They are dev-only transitive dependencies of `eslint-config-next` →
`@next/eslint-plugin-next`, and no patched `braces` release exists. They are not
reachable at runtime.

Do not run `npm audit fix --force` — it would downgrade `eslint-config-next` to
v14.
