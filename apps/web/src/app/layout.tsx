import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Midas — Regime-Aware Portfolio Manager",
  description:
    "AI-powered multi-asset ETF portfolio management with transparent backtests and regime-aware allocation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg-primary text-text-primary antialiased">
        <div className="flex min-h-screen">
          <nav className="w-64 border-r border-border bg-bg-secondary p-6 hidden md:block">
            <div className="mb-8">
              <h1 className="text-xl font-bold text-accent-primary">Midas</h1>
              <p className="text-sm text-text-muted mt-1">Portfolio Manager</p>
            </div>
            <ul className="space-y-2">
              <NavItem href="/" label="Dashboard" />
              <NavItem href="/signals" label="Signals" />
              <NavItem href="/approvals" label="Approvals" />
              <NavItem href="/debate" label="Debate" />
              <NavItem href="/backtests" label="Backtests" />
              <NavItem href="/audit" label="Trade Log" />
              <NavItem href="/settings" label="Settings" />
            </ul>
          </nav>
          <main className="flex-1 p-6 md:p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

function NavItem({ href, label }: { href: string; label: string }) {
  return (
    <li>
      <a
        href={href}
        className="block px-3 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-surface transition-colors"
      >
        {label}
      </a>
    </li>
  );
}
