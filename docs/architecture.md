# Architecture

BlendGuard is four layers that do not mix.

```
DATA  →  MODEL  →  OPTIMIZER  →  PRESENTATION
```

| Layer | Lives in | Responsibility |
| --- | --- | --- |
| DATA | `backend/app/providers/` | Where market information comes from |
| MODEL | `backend/app/optimizer/` | Black-Litterman and portfolio statistics |
| OPTIMIZER | `backend/app/optimizer/` | Find weights satisfying objective + constraints |
| PRESENTATION | `backend/app/api/`, `frontend/` | Explain the result to a normal investor |

**The dependency rule:** imports point only *down* that chain.

- `providers` never imports `optimizer`.
- `optimizer` never imports `api`.
- `optimizer` never imports anything Bloomberg-specific.

A change in one layer must not couple the others.

## DATA — market data providers

All market data is abstracted behind one interface. The optimizer does not know
or care which provider supplied the numbers.

```python
class MarketDataProvider(ABC):
    def get_prices(self, tickers, start, end) -> dict[str, PriceSeries]: ...
    def get_reference_data(self, tickers) -> dict[str, Asset]: ...
    def get_market_caps(self, tickers) -> dict[str, float]: ...
```

Implementations:

| Provider | Use | Notes |
| --- | --- | --- |
| `StubProvider` | tests, offline dev | Deterministic synthetic prices. Never real data. |
| `BloombergProvider` | development & validation | Not a production dependency. See below. |
| Licensed provider | production | Replaceable without touching the optimizer. |

### Normalization

Every provider converts its native payload to the same internal types *before*
anything mathematical runs.

```
Asset       ticker, name, asset_class, region
PriceSeries ticker, start, end, adjusted_close
MarketData  prices, assets, market_caps, metadata, as_of
```

`Asset` is what a *data vendor* can tell you. BlendGuard's curated ETF metadata
(portfolio role, core/satellite exposure, plain-language description, support
status) lives in `app/universe.py` and projects down to `Asset` via
`ETF.to_asset()`. There is exactly one literal table; see
[universe.md](./universe.md).

`MarketData.returns()` is the single definition of a daily return:

```
r_t = P_t / P_(t-1) - 1
```

The first observation is always dropped.

## Caching

The optimizer reads from cache. It never fans out to a provider per request.

```
Provider → scheduled update → data/cache/ → optimizer
```

End-of-day data is sufficient. Real-time prices are not used by the model.

## Bloomberg

Bloomberg is a **development and validation** data source. It is used to validate
historical ETF data, reference data, calculations, expected results, and
backtests.

It is deliberately *not* a production dependency:

- The public application must never require a Bloomberg Terminal.
- Bloomberg access is never exposed through an API endpoint.
- Bloomberg datasets are never distributed through the application.
- Bloomberg data dumps are never committed to this repository.
- `blpapi` is not declared in `pyproject.toml`; it is not on PyPI. Install it
  locally from Bloomberg's package index:

  ```bash
  cd backend
  uv pip install \
    --index-url https://blpapi.bloomberg.com/repository/Python-packages \
    --extra-index-url https://pypi.org/simple blpapi
  ```

  Then set `BLOOMBERG_ENABLED=true` in `.env`.

```
DEVELOPMENT                      PRODUCTION
Bloomberg                        Licensed/public provider
  ↓                                ↓
BloombergProvider                Provider implementation
  ↓                                ↓
normalized data                  normalized data
  ↓                                ↓
optimizer  ←───────────────────── optimizer  (unchanged)
```

## Backend layout

```
backend/app/
├── main.py            FastAPI entrypoint, /health, CORS
├── universe.py        the canonical ETF universe
├── taxonomy.py        classification vocabulary
├── config/            the only place environment variables are read
├── providers/         DATA — MarketDataProvider interface
├── optimizer/         MODEL + OPTIMIZER
│   ├── risk.py              returns, covariance, correlation
│   ├── black_litterman.py   prior, views, posterior expected returns
│   ├── presets.py           Conservative / Balanced / Growth
│   └── allocate.py          constrained optimization
├── services/          orchestration only; contains no finance
├── models/            Pydantic request/response schemas
└── api/               routes
```

## CONFIG — one configuration layer

```
backend/app/config/
├── environment.py   Environment enum + the values that differ per environment
├── settings.py      the schema: one flat reader, one frozen grouped Settings
├── validation.py    fails fast; names the missing variable
└── diagnostics.py   the only sanctioned way to display configuration
```

`app.config` owns the boundary between the process environment and everything
else. **No module outside `app/config/` reads `os.environ`.** Application code
takes a `Settings` and reads typed attributes:

```python
from app.config import get_settings

settings = get_settings()
if settings.features.verbose_explanations:
    ...
```

Three environments — `development`, `testing`, `production` — share one schema.
They differ only in values, so switching environments never needs a code change.
Select with `BLENDGUARD_ENV`; it defaults to `development`, and an unrecognised
value is an error rather than a silent fallback.

Precedence, highest first: environment variable → `.env` → per-environment
profile → schema default.

### Naming convention

| Prefix | Owner | Example |
| --- | --- | --- |
| `BLENDGUARD_*` | BlendGuard | `BLENDGUARD_LOG_LEVEL` |
| `BLOOMBERG_*` | the vendor | `BLOOMBERG_API_KEY` |
| `TIINGO_*`, `FMP_*` | the vendor | `TIINGO_API_KEY` |

Vendor settings keep the vendor's prefix so credentials map one-to-one onto that
vendor's documentation and can be injected verbatim by a deployment platform's
secret store. `.env.example` is the authoritative list.

### Secrets

Every credential is a `pydantic.SecretStr`, so `repr()` renders `********`.
Configuration is never printed: `app.config.diagnostics.redacted_settings()` and
`format_diagnostics()` build a dump from an explicit allowlist, revealing whether
a credential is set but never its value. An explicitly listed secret is redacted
by default, so a newly added one cannot silently become loggable. `/health`
reports only status, version and environment.

### Startup validation

`validate_for_startup()` runs in the FastAPI lifespan, before the first request:

- Production rejects the `stub` provider — it returns synthetic prices, not
  market data.
- Production requires the **selected** provider's credentials, and names the
  variable: `Production configuration requires TIINGO_API_KEY for ...`.
- `BLOOMBERG_ENABLED` must be false in production.
- Development and testing require no credentials at all, so the suite runs with
  no Bloomberg Terminal and no API keys.

Missing configuration is never substituted with a fake value: a placeholder
credential turns into an authentication error much later, which is harder to
diagnose than a startup failure.

### Supplying production secrets

Production credentials are injected as environment variables by the deployment
platform's secret store (GitHub Actions secrets, Fly secrets, Kubernetes
`SecretKeyRef`, and so on). They are never committed, never baked into the
package or a container image, and never written to a committed file. See
`README.md` for the deployment recipe.

## Frontend layout

```
frontend/app/          routes, layout, global styles
frontend/components/   presentational components
frontend/lib/          API client, consumer-facing vocabulary
```

No finance logic lives in the frontend.

## Testing

| Suite | Runner | Command | Notes |
| --- | --- | --- | --- |
| backend | pytest | `make test-backend` | `integration`, `bloomberg` and `slow` markers are opt-in |
| frontend | vitest + Testing Library | `make test-frontend` | jsdom; colocated in `__tests__/` |

Both suites are wired into pre-commit, CI and `make check`, so a green local run
and a green CI run enforce identical rules. Backend runs `mypy --strict`;
frontend test files are inside the `tsc --noEmit` and eslint globs, so a broken
test also fails `make typecheck`.

Frontend tests assert project invariants rather than incidental rendering: the
universe vocabulary stays fully labelled, and consumer-facing copy never exposes
quant jargon. See `frontend/README.md`.

## API

```
POST /api/optimize     optimize a portfolio
GET  /api/universe     the canonical ETF universe (see universe.md)
GET  /api/presets      role-based preset constraints
GET  /health           liveness
```

Conceptual request:

```json
{
  "goal": "balanced",
  "risk_profile": "medium",
  "views": { "US equities": "moderately bullish" },
  "confidence": { "US equities": "medium" },
  "constraints": { "max_single_etf": 0.40, "min_treasuries": 0.10 }
}
```

The response carries asset weights, expected return, expected volatility, model
metadata, and a human-readable explanation for every allocation.

## Security

Never commit `.env`, API keys, database passwords, Bloomberg credentials, or
proprietary datasets. All secrets come from environment variables; see
`.env.example`.
