/** Citation reference types */
export type CitationType = "signal" | "backtest" | "cost" | "news";

/** A citation in a debate agent response */
export interface CitationRef {
  type: CitationType;
  id: string;
  display_value: string;
  verified: boolean;
  external: boolean;
}

/** A message in the debate conversation */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationRef[];
  suggested_followups: string[];
  timestamp: string;
}

/** Counter-scenario result */
export interface CounterScenario {
  description: string;
  expected_drift_1w: number;
  expected_drift_1m: number;
  cost_saved: number;
  risk_change: number;
  historical_analogies: string[];
  citations: CitationRef[];
}
