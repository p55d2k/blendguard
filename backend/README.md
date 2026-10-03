# BlendGuard Backend

FastAPI service: DATA (providers) → MODEL (Black-Litterman) → OPTIMIZER →
PRESENTATION (API).

See [../docs/architecture.md](../docs/architecture.md) and
[../docs/model.md](../docs/model.md).

## Setup

```bash
uv sync                      # creates .venv, installs the dev group
uv run uvicorn app.main:app --reload
```

Requires Python 3.12 (pinned in `.python-version`).

## Layout

```
app/
├── main.py            FastAPI entrypoint
├── universe.py        the fixed initial ETF universe
├── config/            settings from environment variables
├── providers/         DATA — MarketDataProvider interface
│   ├── base.py        Asset / PriceSeries / MarketData + abstract provider
│   └── stub.py        deterministic offline provider for tests
├── optimizer/         MODEL + OPTIMIZER
│   ├── risk.py              returns, covariance, correlation
│   ├── black_litterman.py   prior, views, posterior E(R)
│   ├── presets.py           Conservative / Balanced / Growth
│   └── allocate.py          constrained optimization
├── services/          orchestration only, no finance
├── models/            Pydantic request/response schemas
└── api/               routes
```

**Import rule:** dependencies point only *down* the chain. `providers` must
never import `optimizer`; `optimizer` must never import `api`.

## Commands

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy app              # strict types
uv run pytest                # tests
uv run pytest -m "not integration"   # offline only
```

Pre-commit runs the lint, format, typecheck, and test gates automatically.

## Bloomberg (development / validation only)

`blpapi` is not on PyPI, so it is not declared in `pyproject.toml`:

```bash
uv pip install \
  --index-url https://blpapi.bloomberg.com/repository/Python-packages \
  --extra-index-url https://pypi.org/simple blpapi
```

Then set `BLOOMBERG_ENABLED=true` in `.env`. Bloomberg must stay isolated behind
`MarketDataProvider` and must never be required in production. Details:
[docs/architecture.md](../docs/architecture.md).

## Testing

Financial math is tested aggressively: returns, covariance, Black-Litterman,
view/confidence translation, constraint enforcement, infeasibility reporting,
missing data, and determinism.

Markers:

| Marker | Meaning |
| --- | --- |
| `slow` | long-running or data-dependent |
| `integration` | requires market data or network |
| `bloomberg` | requires a Bloomberg Desktop API session |

The default suite is fully offline and deterministic.
