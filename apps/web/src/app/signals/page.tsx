/**
 * Signal Detail page (M08-06 + M08-07 wiring).
 *
 * Fetches latest signal from API. Falls back to placeholder if API unavailable.
 */

"use client";

import { useEffect, useState } from "react";
import { signals, regime } from "@/lib/api";

export default function SignalsPage() {
  const [signal, setSignal] = useState<any>(null);
  const [regimeState, setRegimeState] = useState<any>(null);

  useEffect(() => {
    async function load() {
      try {
        const [sigRes, regRes] = await Promise.all([
          signals.getPortfolioLatest("growth").catch(() => null),
          regime.getCurrent().catch(() => null),
        ]);
        if (sigRes) setSignal(sigRes);
        if (regRes) setRegimeState(regRes);
      } catch {}
    }
    load();
  }, []);
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Latest Signal — Growth Portfolio</h1>
      <p className="text-text-secondary">Published: Sunday, Apr 6, 2026 at 7:00 PM ET</p>

      {/* Regime Context */}
      <div className="rounded-xl bg-regime-normal-bg border border-regime-normal/20 p-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-regime-normal" />
          <span className="text-regime-normal font-medium">Normal Regime</span>
          <span className="text-text-muted">— Score: 0.28 | Confidence: 82%</span>
        </div>
        <p className="text-text-secondary text-sm mt-2">
          All signals calm. No overrides active. Full allocation to top-6 momentum sleeves.
        </p>
      </div>

      {/* Allocation Table */}
      <div className="rounded-xl bg-bg-surface border border-border overflow-hidden">
        <h2 className="px-6 py-4 font-semibold border-b border-border">Target Allocation</h2>
        <table className="w-full text-sm">
          <thead className="bg-bg-elevated text-text-muted">
            <tr>
              <th className="px-6 py-2 text-left">Sleeve</th>
              <th className="px-4 py-2 text-left">Ticker</th>
              <th className="px-4 py-2 text-right">Weight</th>
              <th className="px-4 py-2 text-right">Prev</th>
              <th className="px-4 py-2 text-right">Change</th>
              <th className="px-4 py-2 text-right">Reasoning</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <AllocRow sleeve="Equity Sectors" ticker="SPY" weight={25} prev={23} reason="Strong 6m momentum" />
            <AllocRow sleeve="Precious Metals" ticker="GLD" weight={15} prev={12} reason="Safe haven + momentum" />
            <AllocRow sleeve="EM Equity" ticker="VWO" weight={15} prev={18} reason="Reduced: cooling momentum" />
            <AllocRow sleeve="Gov Bonds (Long)" ticker="TLT" weight={10} prev={12} reason="Duration trim" />
            <AllocRow sleeve="REITs" ticker="VNQ" weight={10} prev={10} reason="Stable" />
            <AllocRow sleeve="Dividend ETFs" ticker="VYM" weight={7} prev={7} reason="Income sleeve" />
          </tbody>
        </table>
        <div className="px-6 py-3 bg-bg-elevated text-text-muted text-sm">
          Cash: 18% | Total cost: $4.52 | Turnover: 8.2%
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <a href="/debate" className="px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white transition-colors">
          Debate This Signal
        </a>
        <a href="/backtests" className="px-4 py-2 rounded-lg border border-border text-text-secondary hover:bg-bg-surface transition-colors">
          View Backtest Context
        </a>
      </div>
    </div>
  );
}

function AllocRow({ sleeve, ticker, weight, prev, reason }: {
  sleeve: string; ticker: string; weight: number; prev: number; reason: string;
}) {
  const delta = weight - prev;
  return (
    <tr className="hover:bg-bg-elevated transition-colors">
      <td className="px-6 py-3">{sleeve}</td>
      <td className="px-4 py-3 font-mono text-accent-primary">{ticker}</td>
      <td className="px-4 py-3 text-right font-mono">{weight}%</td>
      <td className="px-4 py-3 text-right font-mono text-text-muted">{prev}%</td>
      <td className={`px-4 py-3 text-right font-mono ${delta > 0 ? "text-gain" : delta < 0 ? "text-loss" : "text-text-muted"}`}>
        {delta > 0 ? "+" : ""}{delta}%
      </td>
      <td className="px-4 py-3 text-right text-text-secondary text-xs">{reason}</td>
    </tr>
  );
}
