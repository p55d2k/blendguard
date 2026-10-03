"""Application services: orchestration across DATA -> MODEL -> OPTIMIZER.

Thin coordination layer. It must not contain finance; that belongs in
:mod:`app.optimizer`.
"""

from __future__ import annotations
