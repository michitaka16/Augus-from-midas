/**
 * Auth badge — shows logged-in state at bottom of nav.
 * Client component so it can read localStorage.
 */

"use client";

import { useEffect, useState } from "react";

export default function AuthBadge() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    const has = !!localStorage.getItem("midas_token");
    setLoggedIn(has);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("midas_token");
    localStorage.removeItem("midas_refresh");
    window.location.href = "/login";
  };

  if (loggedIn === null) return null; // SSR / loading

  if (!loggedIn) {
    return (
      <div className="mt-8 pt-4 border-t border-border">
        <a
          href="/login"
          className="block px-3 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white text-center text-sm font-medium transition-colors"
        >
          Sign in
        </a>
      </div>
    );
  }

  return (
    <div className="mt-8 pt-4 border-t border-border">
      <div className="flex items-center gap-2 px-3 py-2 text-text-muted text-sm">
        <div className="w-2 h-2 rounded-full bg-regime-normal" />
        <span>Signed in</span>
      </div>
      <button
        onClick={handleLogout}
        className="w-full text-left px-3 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-surface transition-colors text-sm"
      >
        Sign out
      </button>
    </div>
  );
}
