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
├── universe.py        the canonical ETF universe
├── taxonomy.py        classification vocabulary
├── config/            the only place environment variables are read
│   ├── environment.py   Environment enum + per-environment defaults
│   ├── settings.py      flat reader -> one frozen, grouped Settings
│   ├── validation.py    fails fast, names the missing variable
│   └── diagnostics.py   redacted, safe-to-log dump
├── domain/            shared vocabulary — no framework, no app imports
│   ├── types.py           Ticker, Currency, DomainValidationError, validators
│   ├── etf.py             ETF (the type; the table stays in universe.py)
│   ├── market.py          Price, Return
│   ├── views.py           View, Confidence
│   ├── constraints.py     Constraint, ConstraintSet
│   ├── presets.py         Preset — Conservative / Balanced / Growth
│   └── optimization.py    OptimizationRequest, OptimizationResult
├── providers/         DATA — MarketDataProvider interface
│   ├── base.py        Asset / PriceSeries / MarketData + abstract provider
│   └── stub.py        deterministic offline provider for tests
├── optimizer/         MODEL + OPTIMIZER
│   ├── risk.py              returns, covariance, correlation
│   ├── black_litterman.py   prior, views, posterior E(R)
│   └── allocate.py          constrained optimization
├── services/          orchestration only, no finance
├── models/            Pydantic request/response schemas
└── api/               routes
```

**Import rule:** dependencies point only *down* the chain. `providers` must
never import `optimizer`; `optimizer` must never import `api`.

`app/domain/` sits *beside* that chain, not in it: it is the vocabulary all four
stages share, so it imports nothing third-party and nothing from the rest of
`app`. `app/models/` stays the Pydantic API layer. Both rules are enforced by
tests, in `tests/domain/test_layering.py`.

**Configuration rule:** only `app/config/` may read `os.environ`. Everything else
takes a `Settings`.

**Numeric rule:** every fractional quantity is a plain fraction. `0.25` is 25%.
`Constraint`/`Allocation` reject `25` rather than quietly accepting it.

## Configuration

```python
from app.config import get_settings, validate_for_startup

settings = get_settings()
settings.market_data.provider  # "stub"
settings.features.verbose_explanations
```

`get_settings()` is cached for the process. The FastAPI lifespan calls
`validate_for_startup()` before serving traffic, so bad configuration is a
startup error, not a confusing request failure.

`BLENDGUARD_ENV` selects `development` (default), `testing` or `production`.
Dotenv is read from the repository root, then the working directory; override
with `BLENDGUARD_ENV_FILE`. See [../.env.example](../.env.example).

To print configuration for diagnostics, use the redaction helpers — never print
the model or `os.environ`:

```python
from app.config import format_diagnostics, get_settings

print(format_diagnostics(get_settings()))  # BLOOMBERG_API_KEY=********
```

## Commands

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy app              # strict types
uv run pytest                # tests
uv run pytest -m "not integration"   # offline only
uv run python -c "from app.config import get_settings, validate_for_startup as v; v(get_settings())"  # validate config
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
`MarketDataProvider` and must never be required in production — startup rejects
`BLOOMBERG_ENABLED=true` under `BLENDGUARD_ENV=production`. Details:
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

The default suite is fully offline and deterministic. Configuration tests
(`tests/config/`) are hermetic: they clear the ambient environment and redirect
dotenv discovery, so the suite behaves identically in CI and on a developer
machine that has real Bloomberg credentials in their shell.
