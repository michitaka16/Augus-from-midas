/**
 * Login page (M08-03).
 */

"use client";

import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState("");
  const [showMfa, setShowMfa] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const { auth } = await import("@/lib/api");
      const result = await auth.login(email, password, mfaToken || undefined);
      const res = result as { tokens?: { access_token: string; refresh_token: string }; mfa_required?: boolean; error?: string; status?: number };

      if (res.mfa_required) {
        setShowMfa(true);
        return;
      }
      if (res.error) {
        setError(res.error);
        return;
      }
      if (res.tokens) {
        localStorage.setItem("midas_token", res.tokens.access_token);
        localStorage.setItem("midas_refresh", res.tokens.refresh_token);
        window.location.href = "/";
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-accent-primary">Midas</h1>
          <p className="text-text-secondary mt-2">
            Regime-aware portfolio management
          </p>
        </div>

        <form
          onSubmit={handleLogin}
          className="rounded-xl bg-bg-surface border border-border p-8 space-y-4"
        >
          <div>
            <label htmlFor="email" className="block text-sm text-text-secondary mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-bg-primary border border-border focus:border-accent-primary focus:outline-none"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm text-text-secondary mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-bg-primary border border-border focus:border-accent-primary focus:outline-none"
              required
            />
          </div>

          {showMfa && (
            <div>
              <label htmlFor="mfa" className="block text-sm text-text-secondary mb-1">
                MFA Code
              </label>
              <input
                id="mfa"
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={mfaToken}
                onChange={(e) => setMfaToken(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-bg-primary border border-border focus:border-accent-primary focus:outline-none font-mono text-center text-2xl tracking-widest"
                placeholder="000000"
              />
            </div>
          )}

          {error && (
            <p className="text-loss text-sm">{error}</p>
          )}

          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-medium transition-colors"
          >
            Sign In
          </button>

          <p className="text-center text-text-muted text-sm">
            Don&apos;t have an account?{" "}
            <a href="/signup" className="text-accent-primary hover:underline">
              Sign up
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}
