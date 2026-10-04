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
├── config/            settings from environment variables
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
