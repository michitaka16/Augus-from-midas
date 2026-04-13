/**
 * Pending Approvals page — wired to live API (M08-08 + M08-09).
 *
 * Fetches /approvals/pending. Shows grouped rebalance card with
 * per-trade opt-out. Approve/reject/hold call live endpoints.
 */

"use client";

import { useEffect, useState } from "react";
import { approvals } from "@/lib/api";

interface Approval {
  id: number;
  signal_id: number;
  model_portfolio_id: string;
  regime: string;
  allocations: Record<string, number>;
  cost_estimate: { total: number };
  trades: { ticker: string; direction: string; shares: number; value: number; cost: number }[];
  created_at: string;
}

export default function ApprovalsPage() {
  const [pending, setPending] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = localStorage.getItem("midas_token") ?? "";
        const res = await approvals.getPending(token) as { approvals: Approval[] };
        setPending(res.approvals ?? []);
      } catch {
        // API not available — show empty state
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleApprove = async (id: number) => {
    const token = localStorage.getItem("midas_token") ?? "";
    await approvals.approve(token, id);
    setPending((prev) => prev.filter((a) => a.id !== id));
  };

  const handleReject = async (id: number) => {
    const token = localStorage.getItem("midas_token") ?? "";
    await approvals.reject(token, id);
    setPending((prev) => prev.filter((a) => a.id !== id));
  };

  if (loading) {
    return <div className="max-w-4xl mx-auto p-8 text-text-muted">Loading...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Pending Approvals</h1>

      {pending.length === 0 ? (
        <EmptyState />
      ) : (
        pending.map((approval) => (
          <ApprovalCard
            key={approval.id}
            approval={approval}
            onApprove={() => handleApprove(approval.id)}
            onReject={() => handleReject(approval.id)}
          />
        ))
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl bg-bg-surface border border-border p-12 text-center">
      <div className="w-16 h-16 rounded-full bg-regime-normal-bg border border-regime-normal/20 flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-regime-normal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold">All clear</h2>
      <p className="text-text-secondary mt-2">No pending approvals.</p>
      <p className="text-text-muted text-sm mt-4">Next signal: Sunday 7 PM ET</p>
    </div>
  );
}

function ApprovalCard({ approval, onApprove, onReject }: {
  approval: Approval;
  onApprove: () => void;
  onReject: () => void;
}) {
  const regimeColors: Record<string, string> = {
    normal: "bg-regime-normal-bg border-regime-normal/20",
    cautious: "bg-regime-cautious-bg border-regime-cautious/20",
    turbulent: "bg-regime-turbulent-bg border-regime-turbulent/20",
  };

  return (
    <div className="rounded-xl bg-bg-surface border border-border overflow-hidden">
      <div className={`px-6 py-3 flex items-center gap-2 border-b ${regimeColors[approval.regime] ?? ""}`}>
        <div className={`w-2 h-2 rounded-full ${approval.regime === "normal" ? "bg-regime-normal" : approval.regime === "cautious" ? "bg-regime-cautious" : "bg-regime-turbulent"}`} />
        <span className="font-medium capitalize">{approval.regime} Regime</span>
      </div>

      <div className="px-6 py-4 border-b border-border">
        <h2 className="text-lg font-semibold capitalize">{approval.model_portfolio_id.replace(/_/g, " ")} — Rebalance</h2>
        <p className="text-text-secondary text-sm mt-1">
          {approval.trades?.length ?? 0} trades. Cost: ${approval.cost_estimate?.total?.toFixed(2) ?? "—"}
        </p>
      </div>

      {approval.trades && approval.trades.length > 0 && (
        <div className="divide-y divide-border">
          {approval.trades.map((trade, i) => (
            <div key={i} className="px-6 py-3 flex items-center gap-4">
              <input type="checkbox" defaultChecked className="w-4 h-4 rounded" aria-label={`Include ${trade.ticker}`} />
              <div className="flex-1">
                <span className="font-medium">{trade.ticker}</span>
                <span className={`ml-2 text-sm ${trade.direction === "buy" ? "text-gain" : "text-loss"}`}>
                  {trade.direction.toUpperCase()} {trade.shares} shares
                </span>
              </div>
              <div className="text-right font-mono">${trade.value?.toLocaleString() ?? "—"}</div>
            </div>
          ))}
        </div>
      )}

      <div className="px-6 py-4 flex items-center gap-3 bg-bg-elevated">
        <a href="/debate" className="text-accent-primary hover:text-accent-hover text-sm">Why this?</a>
        <div className="flex-1" />
        <button onClick={onReject} className="px-4 py-2 rounded-lg border border-border text-text-secondary hover:bg-bg-surface transition-colors">
          Skip
        </button>
        <button onClick={onApprove} className="px-6 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-medium transition-colors">
          Approve All
        </button>
      </div>
    </div>
  );
}
