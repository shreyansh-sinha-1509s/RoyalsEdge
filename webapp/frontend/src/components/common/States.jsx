import { AlertTriangle, Database, Inbox, RefreshCw } from 'lucide-react';

export function LoadingState({ label = 'Loading verified analytics data...' }) {
  return (
    <div className="rr-card flex flex-col items-center justify-center gap-3 px-6 py-16 text-center" role="status">
      <div className="h-9 w-9 animate-spin rounded-full border-2 border-rr-pink border-t-transparent" />
      <p className="text-sm font-medium text-rr-lavender">{label}</p>
    </div>
  );
}

export function ErrorState({ error, onRetry, title = 'Unable to load analytical data' }) {
  const message = error?.message || 'An unexpected error occurred while contacting the backend API.';
  return (
    <div
      className="rr-card border-rr-coral/40 bg-rr-coral/5 px-6 py-10 text-center"
      role="alert"
    >
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-rr-coral/15 text-rr-coral">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <h3 className="text-base font-semibold text-rr-light">{title}</h3>
      <p className="mx-auto mt-1.5 max-w-xl text-sm text-rr-lavender">{message}</p>
      <p className="mt-2 text-xs text-rr-lavender/80">
        RoyalsEdge never substitutes fabricated demo data when live backend data is unavailable.
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 inline-flex items-center gap-2 rounded-lg bg-rr-pink px-4 py-2 text-xs font-semibold text-white transition hover:bg-rr-pink/90"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry Request
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title = 'No matching records found',
  description = 'Try relaxing one or more active filters to explore the full 2022–2026 IPL & T20I cohort.',
  action = null,
}) {
  return (
    <div className="rr-card flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-rr-lavender/10 text-rr-lavender">
        <Inbox className="h-5 w-5" />
      </div>
      <h3 className="text-base font-semibold text-rr-light">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-rr-lavender">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, subtitle, actions = null }) {
  return (
    <div className="mb-6 flex flex-col gap-4 border-b border-rr-lavender/15 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && (
          <div className="mb-1.5 inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-rr-pink">
            <Database className="h-3.5 w-3.5" />
            {eyebrow}
          </div>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-rr-light sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1.5 max-w-3xl text-sm text-rr-lavender">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

