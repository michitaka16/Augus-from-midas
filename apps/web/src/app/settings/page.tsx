/**
 * Settings page (M08-18 + M08-19 wiring).
 *
 * Fetches /account for current prefs. Updates via PUT /account/portfolio
 * and PUT /account/preferences.
 */

"use client";

import { useEffect, useState } from "react";
import { account } from "@/lib/api";

export default function SettingsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [activePortfolio, setActivePortfolio] = useState("growth");

  useEffect(() => {
    async function load() {
      try {
        const token = localStorage.getItem("midas_token") ?? "";
        const res = await account.getProfile(token) as any;
        if (res?.preferences) {
          setProfile(res);
          setActivePortfolio(res.preferences.model_portfolio_id);
        }
      } catch {}
    }
    load();
  }, []);

  const handlePortfolioChange = async (id: string) => {
    const token = localStorage.getItem("midas_token") ?? "";
    await account.updatePortfolio(token, id);
    setActivePortfolio(id);
  };
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Portfolio Selection */}
      <Section title="Model Portfolio">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { id: "aggressive_growth", name: "Aggressive Growth", vol: "18%", price: "$29/mo" },
            { id: "growth", name: "Growth", vol: "14%", price: "$29/mo" },
            { id: "balanced", name: "Balanced", vol: "10%", price: "$19/mo" },
            { id: "conservative", name: "Conservative", vol: "6%", price: "$9/mo" },
            { id: "income", name: "Income", vol: "6%", price: "$19/mo" },
          ].map((p) => (
            <button
              key={p.id}
              onClick={() => handlePortfolioChange(p.id)}
              className={`p-4 rounded-xl border text-left transition-colors ${
                activePortfolio === p.id
                  ? "border-accent-primary bg-accent-muted"
                  : "border-border hover:border-border-hover"
              }`}
            >
              <p className="font-medium">{p.name}</p>
              <p className="text-text-muted text-sm mt-1">Vol target: {p.vol} | {p.price}</p>
              {activePortfolio === p.id && (
                <p className="text-accent-primary text-xs mt-1">Active</p>
              )}
            </button>
          ))}
        </div>
      </Section>

      {/* Escalation Timeout */}
      <Section title="Turbulent Regime Timeout">
        <p className="text-text-secondary text-sm mb-3">
          If a turbulent regime is detected and you don&apos;t respond, the system
          will auto-execute a defensive move after this timeout.
        </p>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min={12}
            max={72}
            defaultValue={24}
            className="flex-1"
            aria-label="Timeout hours"
          />
          <span className="font-mono text-lg w-16 text-right">24h</span>
        </div>
        <p className="text-text-muted text-xs mt-1">Range: 12h – 72h</p>
      </Section>

      {/* Notifications */}
      <Section title="Notifications">
        <div className="space-y-3">
          {[
            { label: "Regime changes", key: "regime_changed" },
            { label: "New signals published", key: "signal_published" },
            { label: "Pending approvals", key: "approval_pending" },
            { label: "Execution confirmed", key: "execution_confirmed" },
          ].map((n) => (
            <div key={n.key} className="flex items-center justify-between py-2">
              <span>{n.label}</span>
              <select
                defaultValue="push"
                className="bg-bg-surface border border-border rounded-lg px-3 py-1.5 text-sm"
                aria-label={`Notification preference for ${n.label}`}
              >
                <option value="push">Push</option>
                <option value="email">Email</option>
                <option value="both">Both</option>
                <option value="none">None</option>
              </select>
            </div>
          ))}
        </div>
      </Section>

      {/* IBKR Link */}
      <Section title="Broker Connection">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Interactive Brokers</p>
            <p className="text-text-muted text-sm">Not connected</p>
          </div>
          <button className="px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white transition-colors">
            Link Account
          </button>
        </div>
      </Section>

      {/* Paper Trading */}
      <Section title="Paper Trading">
        <div className="flex items-center justify-between">
          <div>
            <p>Practice mode</p>
            <p className="text-text-muted text-sm">
              Trades execute against a paper account. No real money at risk.
            </p>
          </div>
          <button
            className="w-12 h-6 rounded-full bg-accent-primary relative"
            role="switch"
            aria-checked="true"
            aria-label="Paper trading toggle"
          >
            <div className="w-5 h-5 rounded-full bg-white absolute right-0.5 top-0.5 transition-transform" />
          </button>
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-bg-surface border border-border p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      {children}
    </div>
  );
}
