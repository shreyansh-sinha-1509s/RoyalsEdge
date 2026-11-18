export function KpiCard({ label, value, subtext, accent = 'none', icon: Icon = null }) {
  const accentBar =
    accent === 'pink'
      ? 'border-t-2 border-t-rr-pink'
      : accent === 'gold'
        ? 'border-t-2 border-t-rr-gold'
        : accent === 'teal'
          ? 'border-t-2 border-t-rr-teal'
          : '';

  return (
    <div className={`rr-card p-4 transition hover:border-rr-lavender/35 ${accentBar}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-rr-lavender">
          {label}
        </span>
        {Icon && <Icon className="h-4 w-4 text-rr-pink/80" />}
      </div>
      <div className="mt-2 font-mono text-2xl font-bold tracking-tight text-rr-light tabular-nums">
        {value}
      </div>
      {subtext && <p className="mt-1 text-xs text-rr-lavender/90">{subtext}</p>}
    </div>
  );
}

