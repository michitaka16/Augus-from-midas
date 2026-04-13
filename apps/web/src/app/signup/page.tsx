/**
 * Signup page — create account, choose portfolio, setup MFA.
 */

"use client";

import { useState } from "react";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    try {
      const { auth } = await import("@/lib/api");
      const result = (await auth.signup(email, password)) as {
        user_id?: number;
        error?: string;
        status?: number;
      };

      if (result.error) {
        setError(result.error);
        return;
      }

      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Signup failed");
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="w-full max-w-md text-center">
          <div className="rounded-xl bg-bg-surface border border-border p-8">
            <div className="w-16 h-16 rounded-full bg-regime-normal-bg border border-regime-normal/20 flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-regime-normal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold">Account created</h2>
            <p className="text-text-secondary mt-2">
              You can now sign in and choose your model portfolio.
            </p>
            <a
              href="/login"
              className="mt-6 inline-block px-6 py-3 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-medium transition-colors"
            >
              Sign In
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-accent-primary">Midas</h1>
          <p className="text-text-secondary mt-2">Create your account</p>
        </div>

        <form
          onSubmit={handleSignup}
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
              minLength={8}
            />
          </div>

          <div>
            <label htmlFor="confirm" className="block text-sm text-text-secondary mb-1">
              Confirm Password
            </label>
            <input
              id="confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-bg-primary border border-border focus:border-accent-primary focus:outline-none"
              required
            />
          </div>

          {error && <p className="text-loss text-sm">{error}</p>}

          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-medium transition-colors"
          >
            Create Account
          </button>

          <p className="text-center text-text-muted text-sm">
            Already have an account?{" "}
            <a href="/login" className="text-accent-primary hover:underline">
              Sign in
            </a>
          </p>
        </form>

        <p className="text-text-muted text-xs text-center mt-6">
          Midas is a publisher of impersonal model portfolios. Not investment advice.
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}
