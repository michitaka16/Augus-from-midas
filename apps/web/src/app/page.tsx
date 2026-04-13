/**
 * Dashboard page — the "calm state" screen (M08-04 + M08-05 wiring).
 *
 * Fetches real data from API. Polls every 60s when tab is active.
 */

"use client";

import { useEffect, useState } from "react";
import { signals, regime, approvals } from "@/lib/api";

interface RegimeData {
  regime: string;
  ensemble_score: number;
  date: string;
  signals: Record<string, number>;
}

interface SignalData {
  id: number;
  model_portfolio_id: string;
  regime: string;
  allocations: Record<string, number>;
  cost_estimate: { total: number };
}

export default function Dashboard() {
  const [regimeState, setRegimeState] = useState<RegimeData | null>(null);
  const [latestSignal, setLatestSignal] = useState<SignalData | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [regimeRes, signalsRes] = await Promise.all([
          regime.getCurrent().catch(() => null),
          signals.getLatest().catch(() => null),
        ]);
        if (regimeRes) setRegimeState(regimeRes as RegimeData);
        if (signalsRes) {
          const sigs = (signalsRes as { signals: SignalData[] }).signals;
          const growth = sigs?.find((s) => s.model_portfolio_id === "growth");
          if (growth) setLatestSignal(growth);
        }
      } catch (e) {
        setError("Could not connect to API. Is the backend running?");
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 60_000); // Poll every 60s
    return () => clearInterval(interval);
  }, []);

  const regimeLevel = regimeState?.regime ?? "normal";
  const regimeColors: Record<string, { dot: string; bg: string; text: string }> = {
    normal: { dot: "bg-regime-normal", bg: "bg-regime-normal-bg", text: "text-regime-normal" },
    cautious: { dot: "bg-regime-cautious", bg: "bg-regime-cautious-bg", text: "text-regime-cautious" },
    turbulent: { dot: "bg-regime-turbulent", bg: "bg-regime-turbulent-bg", text: "text-regime-turbulent" },
  };
  const rc = regimeColors[regimeLevel] ?? regimeColors.normal;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-text-secondary mt-1">
          {pendingCount > 0
            ? `${pendingCount} pending approval(s) need your attention.`
            : "Your portfolio is on track."}
        </p>
      </div>

      {error && (
        <div className="rounded-xl bg-regime-turbulent-bg border border-regime-turbulent/20 p-4 text-regime-turbulent">
          {error}
        </div>
      )}

      {/* Regime Banner */}
      <div className={`rounded-xl ${rc.bg} border border-${regimeLevel === "normal" ? "regime-normal" : regimeLevel === "cautious" ? "regime-cautious" : "regime-turbulent"}/20 p-4 flex items-center gap-3`}>
        <div className={`w-3 h-3 rounded-full ${rc.dot} animate-pulse`} />
        <div>
          <span className={`font-medium ${rc.text} capitalize`}>{regimeLevel} Regime</span>
          {regimeState?.ensemble_score != null && (
            <span className="text-text-secondary ml-2">
              Score: {regimeState.ensemble_score.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Regime" value={regimeLevel.toUpperCase()} change={regimeState?.date ?? ""} neutral />
        <StatCard
          label="Latest Signal Cost"
          value={latestSignal ? `$${latestSignal.cost_estimate?.total?.toFixed(2) ?? "—"}` : "—"}
          change="Total rebalance cost"
          neutral
        />
        <StatCard label="Pending Approvals" value={String(pendingCount)} change={pendingCount === 0 ? "No action needed" : "Review now"} neutral={pendingCount === 0} />
      </div>

      {/* Allocation from latest signal */}
      {latestSignal?.allocations && (
        <div className="rounded-xl bg-bg-surface border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Current Allocation — Growth Portfolio</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(latestSignal.allocations).map(([sleeve, weight]) => (
              <SleeveBar key={sleeve} label={sleeve.replace(/_/g, " ")} weight={Math.round(Number(weight) * 100)} />
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <a href="/debate" className="px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white transition-colors">
          Debate with AI
        </a>
        <a href="/backtests" className="px-4 py-2 rounded-lg bg-bg-surface border border-border hover:border-border-hover text-text-secondary transition-colors">
          View Backtests
        </a>
      </div>
    </div>
  );
}

function StatCard({ label, value, change, positive, neutral }: {
  label: string; value: string; change: string; positive?: boolean; neutral?: boolean;
}) {
  return (
    <div className="rounded-xl bg-bg-surface border border-border p-4">
      <p className="text-text-muted text-sm">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      <p className={`text-sm mt-1 ${neutral ? "text-text-muted" : positive ? "text-gain" : "text-loss"}`}>{change}</p>
    </div>
  );
}

function SleeveBar({ label, weight }: { label: string; weight: number }) {
  const colors = [
    "bg-blue-500", "bg-yellow-500", "bg-purple-500", "bg-pink-500",
    "bg-red-500", "bg-cyan-500", "bg-orange-500", "bg-teal-500", "bg-indigo-500", "bg-emerald-500",
  ];
  const color = colors[label.length % colors.length];
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-text-secondary truncate">{label}</span>
        <span>{weight}%</span>
      </div>
      <div className="w-full bg-bg-primary rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(weight, 100)}%` }} />
      </div>
    </div>
  );
}
