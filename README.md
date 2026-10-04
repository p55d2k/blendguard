# BlendGuard

Build a diversified ETF portfolio from your goals, beliefs, and risk limits.

A transparent Black-Litterman portfolio optimizer for ETF-based portfolios with
enforceable per-asset constraints and role-based presets.

```
User preferences → quantitative views → market prior → Black-Litterman
                → constrained optimization → ETF allocation → explanation
```

> BlendGuard is an optimizer and educational decision-support tool. It is not a
> trading platform, a broker, an execution system, or a source of market
> predictions. It does not provide personalized investment advice.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Layers, market-data provider interface, caching, Bloomberg policy, API |
| [docs/universe.md](docs/universe.md) | The canonical nine-ETF universe: metadata, taxonomy, roles, boundaries |
| [docs/model.md](docs/model.md) | Risk estimation, Black-Litterman, view translation, constraints, presets, invariants |
| [docs/README.md](docs/README.md) | Index and documentation conventions |

## Layers

```
DATA          backend/app/providers/   Bloomberg (dev) · licensed provider (prod)
MODEL         backend/app/optimizer/   risk estimation · Black-Litterman
OPTIMIZER     backend/app/optimizer/   constrained weights
PRESENTATION  backend/app/api/ · frontend/   FastAPI · Next.js
```

Imports only ever point downward in that chain. See
[docs/architecture.md](docs/architecture.md).

## Repository layout

```
blendguard/
├── backend/       FastAPI + PyPortfolioOpt (uv, Python 3.12)
├── frontend/      Next.js 16 + React 19 + Tailwind 4 (npm)
├── data/          market-data cache — git-ignored, never committed
├── docs/          model and architecture documentation
├── .github/       CI workflows
├── .env.example   copy to .env; .env is never committed
└── Makefile
```

## Quick start

```bash
make install          # uv sync + npm install
make hooks            # install pre-commit and register the git hook
cp .env.example .env
make dev              # backend :8000 and frontend :3000
```

Then:

- http://localhost:3000 — consumer UI
- http://localhost:8000/docs — OpenAPI

Requires Python 3.12 and Node 22+.

## Configuration

Every runtime setting is declared once in `backend/app/config/`, and nothing
else in the codebase reads environment variables. Three environments share one
schema and are selected with `BLENDGUARD_ENV`:

| | `development` | `testing` | `production` |
| --- | --- | --- | --- |
| log level | `DEBUG` | `WARNING` | `INFO` |
| debug | on | off | off |
| CORS origins | `localhost:3000` | none | none (set explicitly) |
| market-data cache max age | 12h | 0h (never reuse) | 24h |
| Bloomberg | allowed | off | **forbidden** |
| credentials required | no | no | yes, for the selected provider |

`BLENDGUARD_*` is for settings BlendGuard owns; `BLOOMBERG_*`, `TIINGO_*` and
`FMP_*` keep the vendor's prefix so credentials match that vendor's docs and can
be injected verbatim from a deployment secret store.
[`.env.example`](.env.example) is the authoritative list.

Production validates at startup and refuses to serve traffic on bad
configuration, so a missing credential is one clear sentence rather than an
obscure 500 later:

```
ConfigurationError: Production configuration requires TIINGO_API_KEY for
market-data provider 'tiingo'. Inject it as an environment variable via your
deployment platform's secret store; never commit it.
```

Secrets are `SecretStr`, so they render as `********` in logs and diagnostics.
`GET /health` returns only status, version and environment.

## Commands

```bash
make install      # install backend + frontend dependencies
make dev          # run both dev servers
make test         # backend + frontend tests (offline only)
make lint         # ruff + eslint
make typecheck    # mypy --strict + tsc --noEmit
make check        # lint + typecheck + test
make precommit    # run all pre-commit hooks on all files
```

Or directly:

```bash
cd backend
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
uv run mypy app

cd frontend
npm run dev
npm run lint
npm run typecheck
npm test
```

## Quality gates

`make hooks` installs [pre-commit](https://pre-commit.com) once. After that every
commit runs:

| Hook | Scope |
| --- | --- |
| `end-of-file-fixer`, `trailing-whitespace`, `mixed-line-ending` | all files |
| `check-toml`, `check-yaml`, `check-json`, `check-merge-conflict`, `check-case-conflict` | all files |
| `check-added-large-files` (512 KB) | all files |
| `ruff format`, `ruff check --fix`, `ruff format --check` | backend |
| `mypy --strict` | backend |
| `pytest` (offline markers only) | backend |
| `eslint`, `tsc --noEmit`, `vitest` | frontend |

Tests requiring a network, market data, or a Bloomberg session are opt-in and
never run in the default hook:

```bash
pre-commit run pytest-integration --all-files
pre-commit run pytest-bloomberg --all-files
```

CI (`.github/workflows/ci.yml`) runs the same hooks plus a production
`next build`, coverage, and a guard against tracked secrets or licensed market
data. Dependabot watches `uv`, `npm`, and GitHub Actions.

## ETF universe

Nine ETFs, defined once in `backend/app/universe.py` and served to the UI from
`GET /api/universe`. No layer keeps its own ticker list.

| Ticker | Class | Region | Role |
| --- | --- | --- | --- |
| VOO | Equity | US | `us_large_cap_core` |
| VTI | Equity | US | `us_total_market` |
| VEA | Equity | Developed ex-US | `developed_international` |
| VWO | Equity | Emerging Markets | `emerging_markets` |
| HYG | High Yield | US | `high_yield_credit` |
| JNK | High Yield | US | `high_yield_credit` |
| SHY | Treasury | US | `short_duration_treasury` |
| IEF | Treasury | US | `intermediate_treasury` |
| TLT | Treasury | US | `long_duration_treasury` |

See [docs/universe.md](docs/universe.md) for the rationale behind each ETF and
the process for expanding the universe.

## Principles

1. **No secrets in the repository.** `.env`, API keys, database passwords, and
   licensed datasets are never committed. Production credentials arrive only as
   environment variables from a deployment platform's secret store.
2. **Configuration has one owner.** Only `backend/app/config/` reads the
   environment; the rest of the codebase takes a validated `Settings`.
3. **Bloomberg is a development and validation source only**, never a production
   dependency, and never exposed through an API endpoint. Startup rejects
   `BLOOMBERG_ENABLED=true` under `BLENDGUARD_ENV=production`.
4. **Market data is read from cache.** The optimizer does not fan out to
   providers per request.
5. **Constraints are never silently relaxed.** An infeasible constraint set is
   reported as an error.
6. **The Black-Litterman formulation is fixed.** Changes are documented and
   tested in the same change.
7. **Every allocation is explained.** No unexplained "magic" weights.
8. **Complexity is hidden, reasoning is not.** Users are never required to
   understand covariance matrices, `tau`, or solvers.

## License

MIT — see [LICENSE](LICENSE).
