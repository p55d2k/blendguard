# Data

Market data lives here. **Nothing in this directory is committed** except this
README.

```
data/
├── README.md   # tracked
├── cache/      # ignored — end-of-day adjusted closes + reference data
└── raw/        # ignored — provider dumps, never commit or distribute
```

## Rules

- Licensed provider datasets — including Bloomberg's — are never committed or
  distributed.
- The optimizer reads from cache. Only the scheduled update job contacts a
  provider.
- End-of-day data is sufficient; real-time prices are not used by the model.

## Cache layout

| File | Key | Contents |
| --- | --- | --- |
| `cache/prices.parquet` | ticker | `PriceSeries.adjusted_close` |
| `cache/market_caps.parquet` | ticker | `MarketData.market_caps` (USD) |
| `cache/metadata.json` | — | provider name, `as_of`, schema version |
| `cache/reference.parquet` | ticker | `Asset` reference data |

See [../docs/architecture.md](../docs/architecture.md) for the provider
interface and normalization contract.
