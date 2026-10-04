# Docs

| Document | Contents |
| --- | --- |
| [architecture.md](./architecture.md) | The four layers, provider interface, normalization, caching, Bloomberg policy, API surface |
| [universe.md](./universe.md) | The canonical fourteen-ETF universe: metadata, taxonomy, roles, boundaries, how to extend |
| [model.md](./model.md) | Risk estimation, Black-Litterman, view translation, constraints, presets, invariants |

Planned, added as the corresponding code lands:

```
docs/
├── view-translation.md   user sentiment + confidence -> P, Q, Omega
├── presets.md            Conservative / Balanced / Growth constraint tables
└── backtesting.md        methodology and look-ahead-bias controls
```

## Conventions

- The Black-Litterman formulation in `model.md` is fixed. Any change is
  documented here **and** tested in the same change.
- The ETF universe lives in `backend/app/universe.py`; the classification
  vocabulary in `backend/app/taxonomy.py`. There is exactly one literal table.
  Expansions follow the checklist at the end of `universe.md`.
- Preset numbers are product assumptions to be validated through testing, not
  financial truths.
- Allocation explanations are specified, not improvised.
- Market-data internals stay out of documentation and out of the UI.
