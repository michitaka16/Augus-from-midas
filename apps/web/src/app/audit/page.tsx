/**
 * Trade Log / Audit page (M08-14 + M08-15 wiring).
 *
 * Fetches /audit/trail from API. Filterable by event type.
 */

"use client";

import { useEffect, useState } from "react";

interface AuditEntry {
  id: number;
  timestamp: string;
  event_type: string;
  payload: Record<string, unknown>;
  actor: string;
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const token = localStorage.getItem("midas_token") ?? "";
        const params = filter ? `?event_type=${filter}&limit=100` : "?limit=100";
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/audit/trail${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setEntries(data.entries ?? []);
        }
      } catch {}
    }
    load();
  }, [filter]);
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Trade Log</h1>
        <button className="px-4 py-2 rounded-lg border border-border text-text-secondary text-sm hover:bg-bg-surface">
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        {[
          { label: "All", value: null },
          { label: "Signals", value: "signal_published" },
          { label: "Approvals", value: "approval_decided" },
          { label: "Executions", value: "order_filled" },
          { label: "Regime", value: "regime_changed" },
        ].map((f) => (
          <button
            key={f.label}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              filter === f.value
                ? "bg-accent-muted text-accent-primary"
                : "border border-border text-text-muted hover:bg-bg-surface"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Timeline — real data from API */}
      <div className="space-y-2">
        {entries.length === 0 ? (
          <div className="rounded-xl bg-bg-surface border border-border p-8 text-center text-text-muted">
            No audit entries yet. Entries appear after signals are published or trades are executed.
          </div>
        ) : (
          entries.map((entry) => (
            <AuditEntry
              key={entry.id}
              time={entry.timestamp.replace("T", " ").slice(0, 19)}
              type={entry.event_type}
              description={JSON.stringify(entry.payload).slice(0, 200)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function AuditEntry({ time, type, description }: {
  time: string; type: string; description: string;
}) {
  const typeColors: Record<string, string> = {
    signal_published: "text-accent-primary",
    approval_requested: "text-regime-cautious",
    approval_decided: "text-gain",
    order_submitted: "text-regime-cautious",
    order_filled: "text-gain",
    regime_changed: "text-loss",
  };

  return (
    <div className="flex gap-4 rounded-lg bg-bg-surface border border-border p-4 hover:bg-bg-elevated transition-colors">
      <div className="text-text-muted text-sm font-mono w-40 shrink-0">{time}</div>
      <div className={`text-sm font-medium w-36 shrink-0 ${typeColors[type] ?? "text-text-secondary"}`}>
        {type.replace(/_/g, " ")}
      </div>
      <div className="text-text-secondary text-sm">{description}</div>
    </div>
  );
}
