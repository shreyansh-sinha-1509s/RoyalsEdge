import { ChevronLeft, ChevronRight } from 'lucide-react';

export function Pagination({ meta, onPageChange }) {
  if (!meta || meta.totalPages <= 1) return null;
  const { page, totalPages, total, limit } = meta;
  const start = (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);

  return (
    <div className="mt-4 flex flex-col items-center justify-between gap-3 border-t border-rr-lavender/15 pt-4 text-xs text-rr-lavender sm:flex-row">
      <div className="tabular-nums">
        Showing <span className="font-semibold text-rr-light">{start}–{end}</span> of{' '}
        <span className="font-semibold text-rr-light">{total.toLocaleString()}</span> records
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="inline-flex items-center gap-1 rounded-md border border-rr-lavender/25 px-3 py-1.5 font-medium text-rr-light transition hover:border-rr-pink disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Prev
        </button>
        <span className="font-mono tabular-nums">
          Page <strong className="text-rr-light">{page}</strong> / {totalPages}
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="inline-flex items-center gap-1 rounded-md border border-rr-lavender/25 px-3 py-1.5 font-medium text-rr-light transition hover:border-rr-pink disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

