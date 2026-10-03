# ETF Universe

BlendGuard supports **exactly nine ETFs**, defined once in
[`backend/app/universe.py`](../backend/app/universe.py). The classification
vocabulary lives in [`backend/app/taxonomy.py`](../backend/app/taxonomy.py).

The model, the optimizer, the API, and the UI all read from this one table. No
layer keeps its own ticker list.

## The universe

| Ticker | Fund | Asset class | Region | Exposure | Role |
| --- | --- | --- | --- | --- | --- |
| VOO | Vanguard S&P 500 ETF | Equity | US | Core | `us_large_cap_core` |
| VTI | Vanguard Total Stock Market ETF | Equity | US | Core | `us_total_market` |
| VEA | Vanguard FTSE Developed Markets ETF | Equity | Developed ex-US | Core | `developed_international` |
| VWO | Vanguard FTSE Emerging Markets ETF | Equity | Emerging Markets | Core | `emerging_markets` |
| HYG | iShares iBoxx $ High Yield Corporate Bond ETF | High Yield | US | Satellite | `high_yield_credit` |
| JNK | SPDR Bloomberg High Yield Bond ETF | High Yield | US | Satellite | `high_yield_credit` |
| SHY | iShares 1-3 Year Treasury Bond ETF | Treasury | US | Core | `short_duration_treasury` |
| IEF | iShares 7-10 Year Treasury Bond ETF | Treasury | US | Core | `intermediate_treasury` |
| TLT | iShares 20+ Year Treasury Bond ETF | Treasury | US | Core | `long_duration_treasury` |

## Why each ETF exists

**VOO** — US large-company stocks. The default engine of a US equity core.

**VTI** — all US stocks, large and small. Broader and cheaper than VOO. It
overlaps VOO heavily, which is the point: the model should be able to hold
either without pretending they are different asset classes.

**VEA** — stocks from developed markets outside the United States. The
non-negotiable diversifier against a US-only portfolio.

**VWO** — emerging markets. Higher risk, higher long-run growth. Also the
diversifier that behaves differently in a downturn.

**HYG** — lower-rated corporate bonds. More income and default risk than
Treasuries.

**JNK** — a second high-yield fund that overlaps HYG. Keeping both lets
BlendGuard compare like-for-like instruments instead of treating every ticker
as a completely different asset class.

**SHY / IEF / TLT** — short, intermediate, and long US government bonds. Three
points on the duration curve, so the model can express a rate-risk preference
rather than a single blunt "bonds" allocation.

## Taxonomy

Deliberately small. See `app/taxonomy.py`.

**Asset class** — exactly three:

| Value | Tickers |
| --- | --- |
| `equity` | VOO, VTI, VEA, VWO |
| `high_yield` | HYG, JNK |
| `treasury` | SHY, IEF, TLT |

**Region** — exactly three, at portfolio level rather than country level:

| Value | Tickers |
| --- | --- |
| `us` | VOO, VTI, HYG, JNK, SHY, IEF, TLT |
| `developed_ex_us` | VEA |
| `emerging_markets` | VWO |

All fixed-income ETFs are `us`: the initial Treasury and high-yield universe
represents the US fixed-income market.

**Exposure** — `core` (a primary building block) or `satellite` (a deliberate,
smaller add-on). High yield is the only satellite sleeve.

**Role** — why the ETF exists. Roles are *not* unique per ticker; HYG and JNK
share `high_yield_credit` on purpose.

Treasury roles carry an implicit duration rank of 1 (short) → 3 (long), exposed
as `ETF.duration_rank` so explanations can talk about rate sensitivity without
the UI hardcoding ticker order.

## What this universe supports testing for

- US vs international equity allocation
- Developed vs emerging-market exposure
- Equity vs bonds
- High yield vs government bonds
- Short vs intermediate vs long Treasury duration
- Diversification
- Overlapping ETF exposure (VOO/VTI, HYG/JNK)
- Portfolio construction and allocation logic

## What this universe does not represent

Not included, by design:

- Commodities or gold
- REITs
- Cash or money-market funds
- TIPS or inflation-protected bonds
- Municipal bonds
- International bonds
- Individual stocks
- Options or leveraged ETFs
- Sector-specific ETFs

Each would be a separate universe-expansion task.

## Support status

Every record carries `supported`. Unsupported tickers are rejected with
`UnsupportedTickerError` — the universe is never silently widened, so the
optimizer cannot produce an allocation for an instrument BlendGuard does not
model.

```python
from app.universe import require_supported, supported_tickers

require_supported(["VOO", "TLT"])   # ok
require_supported(["QQQ"])          # UnsupportedTickerError
```

## How the UI gets the universe

The frontend never hardcodes a ticker list. It calls `GET /api/universe`,
which projects the canonical table:

```json
{
  "tickers": ["VOO", "VTI", "VEA", "VWO", "HYG", "JNK", "SHY", "IEF", "TLT"],
  "supported_tickers": ["VOO", "..."],
  "etfs": [
    {
      "ticker": "HYG",
      "name": "iShares iBoxx $ High Yield Corporate Bond ETF",
      "asset_class": "high_yield",
      "region": "us",
      "role": "high_yield_credit",
      "exposure": "satellite",
      "description": "Lower-rated corporate bonds. More income and default risk than Treasuries.",
      "supported": true
    }
  ],
  "by_asset_class": { "equity": ["VOO", "VTI", "VEA", "VWO"], "...": [] },
  "by_region": { "us": ["VOO", "VTI", "HYG", "JNK", "SHY", "IEF", "TLT"], "...": [] },
  "asset_class_counts": { "equity": 4, "high_yield": 2, "treasury": 3 },
  "region_counts": { "us": 7, "developed_ex_us": 1, "emerging_markets": 1 }
}
```

## Adding an ETF

A universe expansion is a deliberate change. In one commit:

1. Add the record to `UNIVERSE` in `app/universe.py` with complete metadata.
2. Add any new `AssetClass`, `Region`, `Role`, or `Exposure` member to
   `app/taxonomy.py` — only if the existing vocabulary genuinely cannot express
   the exposure.
3. Update the tables above.
4. Update `EXPECTED_TICKERS` and the derived-class assertions in
   `tests/test_universe.py`.
5. Add a test for whatever the new ETF makes representable.

Do not add an ETF merely to make the list larger.
