import type { RegimeLevel } from "./regime";

/** Weight allocation for a single sleeve */
export interface SleeveWeight {
  sleeve: string;
  ticker: string;
  weight: number;
  prev_weight: number;
  delta: number;
}

/** Transaction cost breakdown for a single trade */
export interface CostBreakdown {
  commission: number;
  sec_fee: number;
  finra_taf: number;
  slippage: number;
  market_impact: number;
  gap_risk: number;
  total: number;
}

/** Published signal for a model portfolio */
export interface Signal {
  id: string;
  model_portfolio_id: string;
  timestamp: string;
  regime: RegimeLevel;
  allocations: SleeveWeight[];
  reasoning: Record<string, string>;
  cost_estimate: CostBreakdown;
}

/** Signal history entry (lighter weight) */
export interface SignalHistoryEntry {
  id: string;
  timestamp: string;
  regime: RegimeLevel;
  total_cost: number;
}
