import { describe, expect, it } from "vitest";

import {
  ASSET_CLASSES,
  ASSET_CLASS_LABELS,
  EXPOSURES,
  REGIONS,
  REGION_LABELS,
  ROLES,
  type ETF,
  type Universe,
  groupByAssetClass,
} from "../universe";

function etf(overrides: Partial<ETF> & Pick<ETF, "ticker" | "asset_class">): ETF {
  return {
    name: overrides.ticker,
    region: "us",
    role: "us_large_cap_core",
    exposure: "core",
    description: "test fixture",
    supported: true,
    ...overrides,
  } as ETF;
}

function universe(etfs: ETF[]): Universe {
  return {
    tickers: etfs.map((e) => e.ticker),
    supported_tickers: etfs.filter((e) => e.supported).map((e) => e.ticker),
    etfs,
    by_asset_class: {},
    by_region: {},
    asset_class_counts: {},
    region_counts: {},
  };
}

describe("vocabulary completeness", () => {
  // These assertions are the point of the file. A new asset class, region or
  // role that someone adds to the union without a user-facing label would
  // render as `undefined` in the UI. Fail here instead.
  it("labels every asset class", () => {
    for (const ac of ASSET_CLASSES) {
      expect(ASSET_CLASS_LABELS[ac], `missing label for asset class "${ac}"`).toBeTruthy();
    }
  });

  it("labels every region", () => {
    for (const r of REGIONS) {
      expect(REGION_LABELS[r], `missing label for region "${r}"`).toBeTruthy();
    }
  });

  it("has no orphan labels that no longer map to a member", () => {
    const acKeys = Object.keys(ASSET_CLASS_LABELS).sort();
    expect(acKeys).toEqual([...ASSET_CLASSES].sort());
    expect(Object.keys(REGION_LABELS).sort()).toEqual([...REGIONS].sort());
  });

  it("keeps exposures and roles non-empty", () => {
    expect(EXPOSURES.length).toBeGreaterThan(0);
    expect(ROLES).toContain("high_yield_credit");
  });
});

describe("groupByAssetClass", () => {
  it("always returns one bucket per asset class, even when empty", () => {
    const groups = groupByAssetClass(universe([]));
    expect([...groups.keys()]).toEqual([...ASSET_CLASSES]);
    expect([...groups.values()].every((v) => v.length === 0)).toBe(true);
  });

  it("routes each ETF to its asset class", () => {
    const groups = groupByAssetClass(
      universe([
        etf({ ticker: "VOO", asset_class: "equity" }),
        etf({ ticker: "TLT", asset_class: "treasury", role: "long_duration_treasury" }),
        etf({ ticker: "HYG", asset_class: "high_yield", role: "high_yield_credit" }),
      ]),
    );
    expect(groups.get("equity")?.map((e) => e.ticker)).toEqual(["VOO"]);
    expect(groups.get("treasury")?.map((e) => e.ticker)).toEqual(["TLT"]);
    expect(groups.get("high_yield")?.map((e) => e.ticker)).toEqual(["HYG"]);
  });

  it("partitions every ETF exactly once", () => {
    const etfs = [
      etf({ ticker: "VOO", asset_class: "equity" }),
      etf({ ticker: "VTI", asset_class: "equity", role: "us_total_market" }),
      etf({ ticker: "IEF", asset_class: "treasury", role: "intermediate_treasury" }),
    ];
    const total = [...groupByAssetClass(universe(etfs)).values()].reduce(
      (n, bucket) => n + bucket.length,
      0,
    );
    expect(total).toBe(etfs.length);
  });
});
