export const RR_COLORS = {
  plum: '#24172C',
  surface: '#392940',
  pink: '#E83E80',
  gold: '#D8B45A',
  light: '#F5F1F5',
  lavender: '#B8A6C2',
  teal: '#4FD1A5',
  coral: '#F26A6A',
  blue: '#7C9EF2',
};

export const RR_TOOLTIP_STYLE = {
  backgroundColor: '#24172C',
  border: '1px solid rgba(184, 166, 194, 0.28)',
  borderRadius: '0.5rem',
  color: '#F5F1F5',
  fontSize: '12px',
  boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
};

export function ChartCard({ title, subtitle, footer, rightSlot = null, children, className = '' }) {
  return (
    <section className={`rr-card flex flex-col p-4 sm:p-5 ${className}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-rr-light sm:text-base">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-rr-lavender">{subtitle}</p>}
        </div>
        {rightSlot}
      </div>
      <div className="w-full flex-1">{children}</div>
      {footer && (
        <div className="mt-3 border-t border-rr-lavender/10 pt-2 text-[11px] text-rr-lavender/80">
          {footer}
        </div>
      )}
    </section>
  );
}

