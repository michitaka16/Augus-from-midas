/** Model portfolio definition */
export interface ModelPortfolio {
  id: string;
  name: string;
  description: string;
  vol_target: number;
  style: "aggressive_growth" | "growth" | "balanced" | "conservative" | "income";
  monthly_price_usd: number;
}

/** Portfolio performance summary */
export interface PortfolioSummary {
  model_portfolio_id: string;
  current_value: number;
  change_today: number;
  change_today_pct: number;
  change_week: number;
  change_week_pct: number;
  pnl_vs_benchmark: number;
}

/** Performance metrics over a time horizon */
export interface PerformanceMetrics {
  horizon: string;
  sharpe: number;
  max_drawdown: number;
  annual_turnover: number;
  cost_drag_pct: number;
  total_return: number;
  annualized_return: number;
}
