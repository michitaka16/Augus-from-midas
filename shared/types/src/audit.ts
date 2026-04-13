/** Audit event types */
export type AuditEventType =
  | "signal_published"
  | "regime_changed"
  | "approval_requested"
  | "approval_decided"
  | "order_submitted"
  | "order_filled"
  | "escalation_step"
  | "user_action";

/** Audit trail entry */
export interface AuditEntry {
  id: string;
  prev_hash: string;
  timestamp: string;
  event_type: AuditEventType;
  payload: Record<string, unknown>;
  actor: string;
}
