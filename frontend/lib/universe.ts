/** Types mirroring the backend universe vocabulary (see docs/universe.md).
 *
 * The UI must never hardcode a ticker list. Fetch `GET /api/universe` and
 * enumerate from the response. Values are stable strings shared with
 * `backend/app/taxonomy.py`.
 */

export const ASSET_CLASSES = [
  "equity",
  "high_yield",
  "treasury",
  "investment_grade",
  "emerging_debt",
] as const;
export type AssetClass = (typeof ASSET_CLASSES)[number];

export const REGIONS = ["us", "developed_ex_us", "emerging_markets", "singapore"] as const;
export type Region = (typeof REGIONS)[number];

export const CURRENCIES = ["usd", "sgd"] as const;
export type Currency = (typeof CURRENCIES)[number];

export const EXPOSURES = ["core", "satellite"] as const;
export type Exposure = (typeof EXPOSURES)[number];

export const ROLES = [
  "us_large_cap_core",
  "us_total_market",
  "developed_international",
  "emerging_markets",
  "singapore_large_cap",
  "high_yield_credit",
  "investment_grade_credit",
  "em_local_currency_debt",
  "short_duration_treasury",
  "intermediate_treasury",
  "long_duration_treasury",
] as const;
export type Role = (typeof ROLES)[number];

export const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Stocks",
  high_yield: "High-yield bonds",
  treasury: "Government bonds",
  investment_grade: "Investment-grade bonds",
  emerging_debt: "Emerging-market bonds",
};

export const REGION_LABELS: Record<Region, string> = {
  us: "United States",
  developed_ex_us: "Developed markets outside the US",
  emerging_markets: "Emerging markets",
  singapore: "Singapore",
};

export const CURRENCY_LABELS: Record<Currency, string> = {
  usd: "US dollars",
  sgd: "Singapore dollars",
};

export interface ETF {
  ticker: string;
  name: string;
  asset_class: AssetClass;
  region: Region;
  currency: Currency;
  role: Role;
  exposure: Exposure;
  description: string;
  supported: boolean;
}

export interface Universe {
  tickers: string[];
  supported_tickers: string[];
  etfs: ETF[];
  by_asset_class: Record<string, string[]>;
  by_region: Record<string, string[]>;
  asset_class_counts: Record<string, number>;
  region_counts: Record<string, number>;
}

export async function fetchUniverse(): Promise<Universe> {
  const { API_URL } = await import("./api");
  const res = await fetch(`${API_URL}/api/universe`, { cache: "no-store" });

  if (!res.ok) {
    throw new Error(`Failed to load the ETF universe: ${res.status}`);
  }

  return (await res.json()) as Universe;
}

export function groupByAssetClass(universe: Universe): Map<AssetClass, ETF[]> {
  const groups = new Map<AssetClass, ETF[]>(
    ASSET_CLASSES.map((ac) => [ac, [] as ETF[]]),
  );
  for (const etf of universe.etfs) {
    groups.get(etf.asset_class)?.push(etf);
  }
  return groups;
}
