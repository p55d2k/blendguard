# Model

The quantitative core: risk estimation, the Black-Litterman posterior, and
constrained optimization. See [architecture.md](./architecture.md) for the layer
boundaries.

## ETF universe

Fixed and small on purpose. A small, understandable universe keeps the model
validatable and the UI explainable.

| Asset class | Tickers |
| --- | --- |
| Equity | VOO, VTI, VEA, VWO |
| High yield | HYG, JNK |
| Treasury | SHY, IEF, TLT |

Defined once in `backend/app/universe.py`. Expanding it is a deliberate,
documented change — not an accident of whatever data happens to be available.

## Stage 1 — market data and risk estimation

Historical prices produce daily simple returns:

```
r_t = P_t / P_(t-1) - 1
```

From those returns:

```
E(R_p)   = w^T mu          portfolio expected return
sigma^2  = w^T Sigma w     portfolio variance
```

where `w` is portfolio weights, `mu` expected asset returns, and `Sigma` the
covariance matrix.

## Stage 2 — Black-Litterman

Black-Litterman combines three things:

1. a market-based prior,
2. investor views,
3. investor confidence.

```
MARKET PRIOR  +  USER VIEWS  +  VIEW CONFIDENCE
                    ↓
            POSTERIOR EXPECTED RETURNS
```

The posterior expected-return formulation:

```
E(R) = [ (tau Sigma)^-1 + P^T Omega^-1 P ]^-1
       [ (tau Sigma)^-1 Pi  + P^T Omega^-1 Q ]
```

| Symbol | Meaning |
| --- | --- |
| `Pi` | market-implied equilibrium returns |
| `Sigma` | covariance matrix |
| `tau` | uncertainty scaling factor |
| `P` | view matrix |
| `Q` | investor views |
| `Omega` | uncertainty / confidence matrix |

This formulation is fixed. Any change must be documented here and covered by
tests.

## View and confidence translation

Users never see `P`, `Q`, or `Omega`. They answer questions in plain language.

| User input | Values |
| --- | --- |
| Goal | Preserve wealth · Balanced growth · Long-term growth |
| Risk | Lower · Medium · Higher |
| Market view | Bearish · Neutral · Bullish |
| Confidence | Low · Medium · High |

Example:

```
User says:  "I am moderately bullish on US equities."
Becomes:    VOO expected return view = +X%,   Omega set from "medium" confidence
```

The exact numeric mapping is a product decision. It must be documented in
`docs/view-translation.md` and covered by tests. It is deliberately **not**
hard-coded in prose: the tables live in code where they are tested.

## Stage 3 — constrained optimization

Objective:

```
maximize   w^T mu - lambda * w^T Sigma w
```

Subject to:

```
sum(w_i) = 1
lower_i  <= w_i <= upper_i
```

Additional constraints may include:

- total equity allocation limits
- total bond allocation limits
- maximum single-asset exposure
- minimum Treasury allocation
- long-only portfolios

Implementation uses PyPortfolioOpt / CVXPY. These libraries are trusted for the
numerical work; the project is responsible for understanding and testing what
they produce.

### Hard rule

**The optimizer must never silently violate a user-selected constraint.**

If the constraint set is infeasible, that is reported as an error, not resolved
by relaxing bounds.

## Invariants

Every optimization result must satisfy:

```
sum(weights) ≈ 1
```

and, for every constrained asset:

```
min_weight <= weight <= max_weight
```

unless the optimizer explicitly reports infeasibility.

## Role-based presets

Presets simplify the problem for ordinary users. They are **product
assumptions, not universal financial truths**, and must not be presented as
objectively correct portfolios.

| Preset | Shape |
| --- | --- |
| Conservative | Higher Treasury exposure, tighter equity limits |
| Balanced | Moderate equity and fixed-income exposure |
| Growth | Higher equity exposure, looser Treasury minimums |

Concrete numbers (equity max, Treasury min, single-ETF max) live in
`app/optimizer/presets.py` and are documented in `docs/presets.md`.

## Explainability

Explainability is a feature, not an afterthought. Every material allocation
ships with a human-readable explanation.

```
VOO
42%

Why?
  +  Positive user view on US equities
  +  Favorable Black-Litterman posterior return
  +  Fits selected growth profile
  -  Limited by maximum equity allocation
  -  Correlated with other US equity ETFs
```

The product should answer four questions:

1. Why did an asset receive its allocation?
2. Why did it not receive a *larger* allocation?
3. Which constraint limited it?
4. How does changing a view change the outcome?

Unexplained "magic" allocations are a defect.

## Product philosophy

> Hide complexity from the user. Do not hide the reasoning.

The user should never be required to understand covariance matrices,
risk-aversion parameters, `tau`, the Black-Litterman equations, efficient
frontiers, or optimization solvers. Those belong behind optional "How this
works" panels.

## Non-goals

BlendGuard is an optimizer and educational decision-support tool. It is **not**:

- a trading platform or broker
- an execution system
- a stock-price prediction engine
- an AI financial adviser
- a source of guaranteed returns
- dependent on a Bloomberg Terminal for end users

No options, futures, cryptocurrency, intraday or high-frequency data, and no
market-prediction claims.

## Testing requirements

Financial calculations are tested aggressively: return calculation, covariance,
Black-Litterman, view translation, confidence translation, optimization,
minimum constraints, maximum constraints, `sum(weights) == 1`, long-only
behaviour, impossible constraints, missing market data, duplicate assets,
numerical instability, and determinism where expected.

## Backtesting

Backtesting is added after the core optimizer works. It must avoid look-ahead
bias: at each historical date use only information available on that date, build
the prior from that information, apply the historical views, optimize, then step
forward. Results are presented as historical simulations, never as predictions
of future performance.
