"""MODEL + OPTIMIZER layers.

MODEL -- risk estimation and Black-Litterman posterior returns (see docs/model.md).

    risk.py             returns, covariance, correlation
    black_litterman.py  market prior, views, posterior E(R)
    presets.py          Conservative / Balanced / Growth constraints

OPTIMIZER -- constrained weight selection (see docs/model.md).

    allocate.py         objective + constraints via PyPortfolioOpt/CVXPY

Import rules: may depend on :mod:`app.providers` (DATA). Must not import the
PRESENTATION layer (:mod:`app.api`).
"""

from __future__ import annotations
