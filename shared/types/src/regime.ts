/** Regime state as detected by the ensemble detector */
export type RegimeLevel = "normal" | "cautious" | "turbulent";

/** Individual signal value in the ensemble */
export interface SignalValue {
  name: string;
  value: number;
  weight: number;
  contribution: number;
}

/** Current regime state snapshot */
export interface RegimeState {
  regime: RegimeLevel;
  confidence: number;
  ensemble_score: number;
  signal_values: SignalValue[];
  overrides_active: string[];
  timestamp: string;
}

/** A historical regime transition */
export interface RegimeTransition {
  id: string;
  from_regime: RegimeLevel;
  to_regime: RegimeLevel;
  timestamp: string;
  signal_values: SignalValue[];
  overrides_active: string[];
}
