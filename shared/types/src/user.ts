/** User profile */
export interface User {
  id: string;
  email: string;
  created_at: string;
  mfa_enabled: boolean;
}

/** Notification channel preference */
export type NotificationChannel = "push" | "email" | "both" | "none";

/** Per-category notification settings */
export interface NotificationSettings {
  regime_change: NotificationChannel;
  signal_published: NotificationChannel;
  approval_pending: NotificationChannel;
  execution_confirmed: NotificationChannel;
}

/** User preferences (lives client-side of the publisher/subscriber boundary) */
export interface UserPreferences {
  model_portfolio_id: string;
  notification_settings: NotificationSettings;
  timeout_hours: number;
  paper_trading: boolean;
}
