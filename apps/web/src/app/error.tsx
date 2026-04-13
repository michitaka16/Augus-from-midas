/**
 * Global error boundary — catches unhandled errors in any page.
 * Shows a friendly message instead of a blank screen.
 */

"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <div className="max-w-md text-center">
        <div className="w-16 h-16 rounded-full bg-regime-turbulent-bg border border-regime-turbulent/20 flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-8 h-8 text-regime-turbulent"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
        <p className="text-text-secondary mb-6">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
        <button
          onClick={reset}
          className="px-6 py-3 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-medium transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
