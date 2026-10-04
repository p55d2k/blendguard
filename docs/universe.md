# ETF Universe

BlendGuard supports **exactly fourteen ETFs**, defined once in
[`backend/app/universe.py`](../backend/app/universe.py). The classification
vocabulary lives in [`backend/app/taxonomy.py`](../backend/app/taxonomy.py).

The model, the optimizer, the API, and the UI all read from this one table. No
layer keeps its own ticker list.

## The universe

| Ticker | Fund | Asset class | Region | Currency | Exposure | Role |
| --- | --- | --- | --- | --- | --- | --- |
| VOO | Vanguard S&P 500 ETF | Equity | US | USD | Core | `us_large_cap_core` |
| SPY | SPDR S&P 500 ETF Trust | Equity | US | USD | Core | `us_large_cap_core` |
| VTI | Vanguard Total Stock Market ETF | Equity | US | USD | Core | `us_total_market` |
| VEA | Vanguard FTSE Developed Markets ETF | Equity | Developed ex-US | USD | Core | `developed_international` |
| VWO | Vanguard FTSE Emerging Markets ETF | Equity | Emerging Markets | USD | Core | `emerging_markets` |
| STTF | State Street SPDR Straits Times Index ETF | Equity | Singapore | SGD | Core | `singapore_large_cap` |
| HYG | iShares iBoxx $ High Yield Corporate Bond ETF | High Yield | US | USD | Satellite | `high_yield_credit` |
| JNK | SPDR Bloomberg High Yield Bond ETF | High Yield | US | USD | Satellite | `high_yield_credit` |
| USHY | iShares Broad USD High Yield Corporate Bond ETF | High Yield | US | USD | Satellite | `high_yield_credit` |
| LQD | iShares iBoxx $ Investment Grade Corporate Bond ETF | Investment Grade | US | USD | Core | `investment_grade_credit` |
| SHY | iShares 1-3 Year Treasury Bond ETF | Treasury | US | USD | Core | `short_duration_treasury` |
| IEF | iShares 7-10 Year Treasury Bond ETF | Treasury | US | USD | Core | `intermediate_treasury` |
| TLT | iShares 20+ Year Treasury Bond ETF | Treasury | US | USD | Core | `long_duration_treasury` |
| LEMB | iShares J.P. Morgan EM Local Currency Bond ETF | Emerging Debt | Emerging Markets | USD | Satellite | `em_local_currency_debt` |

## Why each ETF exists

**VOO** — US large-company stocks. The default engine of a US equity core.

**SPY** — the other S&P 500 tracker. It holds the same index as VOO, so the two
belong to one sleeve; keeping both lets BlendGuard compare like-for-like
instruments instead of pretending they are different asset classes.

**VTI** — all US stocks, large and small. Broader and cheaper than VOO. It
overlaps VOO heavily, which is the point: the model should be able to hold
either without pretending they are different asset classes.

**VEA** — stocks from developed markets outside the United States. The
non-negotiable diversifier against a US-only portfolio.

**VWO** — emerging markets. Higher risk, higher long-run growth. Also the
diversifier that behaves differently in a downturn.

**STTF** — the blue-chip companies listed in Singapore. A single-country equity
sleeve priced in Singapore dollars, so it carries a currency risk nothing else
in the universe does. `Region.SINGAPORE` exists because of it: this fund *is* the
Singapore exposure, so folding it into a wider regional bucket would advertise a
diversification the model cannot deliver.

**HYG** — lower-rated corporate bonds. More income and default risk than
Treasuries.

**JNK** — a second high-yield fund that overlaps HYG. Keeping both lets
BlendGuard compare like-for-like instruments instead of treating every ticker
as a completely different asset class.

**USHY** — high yield issued in dollars, including issuers outside the United
States. The widest of the three high-yield funds, and the same purpose as the
other two.

**LQD** — investment-grade corporate bonds. The rung between Treasuries and high
yield: more income than government bonds, far less default risk than junk. Core,
not satellite, because it is a building block rather than an add-on.

**SHY / IEF / TLT** — short, intermediate, and long US government bonds. Three
points on the duration curve, so the model can express a rate-risk preference
rather than a single blunt "bonds" allocation.

**LEMB** — emerging-market bonds held in their own local currencies. Currency
risk on top of issuer credit risk. Priced in dollars, so it is not the same thing
as holding the currencies: `currency` records the trading currency, not the
exposure.

## Ticker symbols

Symbols are stored as the primary listing ticker, uppercase, with no exchange
suffix, matching the existing universe. `STTF` is the exception that proves the
rule: SGX's stock code is `ES3`, but `STTF` is the symbol BlendGuard uses because
it is the one a provider resolves unambiguously.

## Taxonomy

Deliberately small. See `app/taxonomy.py`.

**Asset class** — five:

| Value | Tickers |
| --- | --- |
| `equity` | VOO, SPY, VTI, VEA, VWO, STTF |
| `high_yield` | HYG, JNK, USHY |
| `treasury` | SHY, IEF, TLT |
| `investment_grade` | LQD |
| `emerging_debt` | LEMB |

Credit quality is modelled separately because it is what a user's beliefs are
usually about: investment-grade corporate credit, speculative high yield, and
emerging-market sovereign credit behave differently in the same shock.

**Region** — four, at portfolio level rather than country level:

| Value | Tickers |
| --- | --- |
| `us` | VOO, SPY, VTI, HYG, JNK, USHY, LQD, SHY, IEF, TLT |
| `developed_ex_us` | VEA |
| `emerging_markets` | VWO, LEMB |
| `singapore` | STTF |

The US Treasury, investment-grade and high-yield markets are US markets. LEMB
follows its exposure, not its listing venue: an emerging-market bond fund listed
in dollars is still emerging-market debt.

**Currency** — the currency an ETF is *priced* in, from
`app.domain.types.Currency`: `usd` for everything except `sgd` (STTF). It is not
the exposure's currency — LEMB is `usd` while holding local-currency bonds.

**Exposure** — `core` (a primary building block) or `satellite` (a deliberate,
smaller add-on). Satellites are the extra credit-risk sleeves: the three
high-yield funds and LEMB.

**Role** — why the ETF exists. Roles are *not* unique per ticker; VOO and SPY
share `us_large_cap_core`, and HYG, JNK and USHY share `high_yield_credit`, on
purpose.

Treasury roles carry an implicit duration rank of 1 (short) → 3 (long), exposed
as `ETF.duration_rank` so explanations can talk about rate sensitivity without
the UI hardcoding ticker order.

## What this universe supports testing for

- US vs international equity allocation
- Developed vs emerging-market exposure
- Equity vs bonds
- Credit quality: government vs investment grade vs high yield vs emerging debt
- Short vs intermediate vs long Treasury duration
- Diversification
- Overlapping ETF exposure (VOO/SPY, VTI, HYG/JNK/USHY)
- Currency exposure (a USD portfolio with one SGD sleeve)
- Portfolio construction and allocation logic

## What this universe does not represent

Not included, by design:

- Commodities or gold
- REITs
- Cash or money-market funds
- TIPS or inflation-protected bonds
- Municipal bonds
- Developed-market bonds, and hard-currency EM debt
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
  "tickers": ["VOO", "SPY", "VTI", "VEA", "VWO", "STTF", "HYG", "JNK", "USHY", "LQD", "SHY", "IEF", "TLT", "LEMB"],
  "supported_tickers": ["VOO", "..."],
  "etfs": [
    {
      "ticker": "HYG",
      "name": "iShares iBoxx $ High Yield Corporate Bond ETF",
      "asset_class": "high_yield",
      "region": "us",
      "currency": "usd",
      "role": "high_yield_credit",
      "exposure": "satellite",
      "description": "Lower-rated corporate bonds. More income and default risk than Treasuries.",
      "supported": true
    }
  ],
  "by_asset_class": { "equity": ["VOO", "SPY", "VTI", "VEA", "VWO", "STTF"], "...": [] },
  "by_region": { "us": ["VOO", "SPY", "VTI", "HYG", "JNK", "USHY", "LQD", "SHY", "IEF", "TLT"], "...": [] },
  "asset_class_counts": { "equity": 6, "high_yield": 3, "treasury": 3, "investment_grade": 1, "emerging_debt": 1 },
  "region_counts": { "us": 10, "developed_ex_us": 1, "emerging_markets": 2, "singapore": 1 }
}
```

## Adding an ETF

A universe expansion is a deliberate change. In one commit:

1. Verify the instrument first: confirm the fund, its official name and its
   classification. A ticker that cannot be resolved to a specific fund is not
   added on a guess — it is marked for clarification instead.
2. Add the record to `UNIVERSE` in `app/universe.py` with complete metadata.
3. Add any new `AssetClass`, `Region`, `Role`, or `Exposure` member to
   `app/taxonomy.py` — only if the existing vocabulary genuinely cannot express
   the exposure. Add a `Currency` member only if the fund is not priced in a
   currency the universe already has.
4. Update the tables above.
5. Update `EXPECTED_TICKERS` and the derived-class assertions in
   `tests/test_universe.py`.
6. Add a test for whatever the new ETF makes representable.

Duplicates are not added: a ticker already in the table is left alone, even if
the request listed it again.

Do not add an ETF merely to make the list larger.
