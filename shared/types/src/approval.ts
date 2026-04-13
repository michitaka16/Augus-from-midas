import type { Signal, CostBreakdown } from "./signal";
import type { RegimeLevel } from "./regime";

/** Approval status */
export type ApprovalStatus = "pending" | "approved" | "rejected" | "held" | "timeout_auto";

/** Escalation state for turbulent regime */
export interface EscalationState {
  regime: RegimeLevel;
  started_at: string;
  timeout_at: string;
  reminder_sent: boolean;
  auto_defensive_scheduled: boolean;
}

/** A pending approval for a rebalance */
export interface Approval {
  id: string;
  signal_id: string;
  signal: Signal;
  status: ApprovalStatus;
  created_at: string;
  decided_at: string | null;
  method: "manual" | "timeout_auto" | null;
  escalation: EscalationState | null;
}

/** Trade within an approval (for per-item opt-out) */
export interface TradeItem {
  ticker: string;
  direction: "buy" | "sell";
  shares: number;
  estimated_value: number;
  cost: CostBreakdown;
  included: boolean;
}
