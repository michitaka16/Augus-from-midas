import type { PerformanceMetrics } from "./portfolio";
import type { RegimeLevel } from "./regime";

/** Regime-conditional performance stats */
export interface RegimeConditionalStats {
  regime: RegimeLevel;
  sharpe: number;
  annualized_return: number;
  annualized_vol: number;
  max_drawdown: number;
  avg_drawdown_duration_days: number;
}

/** Benchmark comparison */
export interface BenchmarkComparison {
  name: string;
  sharpe: number;
  total_return: number;
  max_drawdown: number;
  cost_drag_pct: number;
}

/** Full backtest run results */
export interface BacktestRun {
  id: string;
  model_portfolio_id: string;
  started_at: string;
  horizons: PerformanceMetrics[];
  regime_stats: RegimeConditionalStats[];
  benchmarks: BenchmarkComparison[];
  deflated_sharpe: number;
  pbo: number;
  worst_12m_return: number;
  worst_drawdown: number;
  worst_drawdown_duration_days: number;
}
