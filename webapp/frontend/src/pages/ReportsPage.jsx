import { Download, FileSpreadsheet, FileText, ShieldCheck } from 'lucide-react';
import { ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtBytes, fmtDateTime } from '../utils/formatters.js';

export function ReportsPage() {
  const reportsQ = useApiQuery((signal) => api.getReports(signal), []);

  if (reportsQ.loading) return <LoadingState label="Loading official submission reports catalog..." />;
  if (reportsQ.error) return <ErrorState error={reportsQ.error} onRetry={reportsQ.refetch} />;
  const reports = reportsQ.data || [];

  const submissionDocs = reports.filter((r) => r.category === 'Official Submission');
  const appendixDocs = reports.filter((r) => r.category !== 'Official Submission');

  const renderCard = (doc) => {
    const Icon = doc.fileType === 'XLSX' || doc.fileType === 'CSV' ? FileSpreadsheet : FileText;
    return (
      <div key={doc.id} className="rr-card flex flex-col justify-between p-5">
        <div>
          <div className="flex items-start justify-between gap-2">
            <span className="rounded bg-rr-plum px-2 py-0.5 font-mono text-[10px] font-bold text-rr-gold">
              {doc.fileType}
            </span>
            <Icon className="h-5 w-5 text-rr-pink" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-rr-light">{doc.title}</h3>
          <p className="mt-1.5 text-xs leading-relaxed text-rr-lavender">{doc.description}</p>
        </div>

        <div className="mt-5 border-t border-rr-lavender/15 pt-3">
          <div className="mb-3 flex items-center justify-between text-[11px] text-rr-lavender">
            <span className="font-mono">{fmtBytes(doc.sizeBytes)}</span>
            <span>Generated: {fmtDateTime(doc.lastGeneratedAt)}</span>
          </div>
          {doc.available ? (
            <a
              href={api.getReportDownloadUrl(doc.id)}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-rr-pink px-3.5 py-2 text-xs font-bold text-white transition hover:bg-rr-pink/90"
            >
              <Download className="h-3.5 w-3.5" />
              Download {doc.fileType}
            </a>
          ) : (
            <span className="block rounded-lg border border-rr-coral/35 py-2 text-center text-xs text-rr-coral">
              File currently unavailable on server
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Verified Competition Deliverables · Allowlisted Downloads"
        title="Reports & Official Downloads"
        subtitle="Direct, read-only downloads streamed from the verified Phase 6 submission/ package and analytical outputs. Zero duplicate or recalculated rankings."
      />

      <div className="flex items-start gap-3 rounded-xl border border-rr-teal/35 bg-rr-teal/10 p-4 text-xs">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-rr-teal" />
        <div>
          <div className="font-bold text-rr-teal">Single Source of Truth Guarantee</div>
          <p className="mt-1 text-rr-light/90">
            Every CSV, Excel sheet, and PDF below is served directly from the verified Phase 6 submission directory and
            reconciled against the PostgreSQL rankings tables.
          </p>
        </div>
      </div>

      <section>
        <h2 className="mb-4 text-base font-bold text-rr-light">Official Round 1 Submission Package</h2>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {submissionDocs.map(renderCard)}
        </div>
      </section>

      {appendixDocs.length > 0 && (
        <section>
          <h2 className="mb-4 text-base font-bold text-rr-light">Analytical Appendix &amp; Audit Tables</h2>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {appendixDocs.map(renderCard)}
          </div>
        </section>
      )}
    </div>
  );
}

