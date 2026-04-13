/**
 * 404 page — friendly not-found with link back to dashboard.
 */

export default function NotFound() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <div className="max-w-md text-center">
        <h1 className="text-6xl font-bold text-text-muted mb-4">404</h1>
        <h2 className="text-xl font-semibold mb-2">Page not found</h2>
        <p className="text-text-secondary mb-6">
          This page doesn&apos;t exist. Head back to the dashboard.
        </p>
        <a
          href="/"
          className="px-6 py-3 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-medium transition-colors inline-block"
        >
          Go to Dashboard
        </a>
      </div>
    </div>
  );
}
