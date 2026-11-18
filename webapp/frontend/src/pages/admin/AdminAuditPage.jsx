import { FileText } from 'lucide-react';
import { useState } from 'react';
import { Pagination } from '../../components/common/Pagination.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../../components/common/States.jsx';
import { useApiQuery } from '../../hooks/useApiQuery.js';
import { api } from '../../services/api.js';
import { fmtDateTime } from '../../utils/formatters.js';

export function AdminAuditPage() {
  const [page, setPage] = useState(1);
  const logsQ = useApiQuery((signal) => api.adminAuditLogs({ page, limit: 25 }, signal), [page]);

  return (
    <div>
      <PageHeader
        eyebrow="Security & Operational Audit Trail"
        title="Audit & System Logs"
        subtitle="Chronological log of admin authentication, cache refreshes, reconciliations, and CSV imports. Credentials and tokens are never logged."
      />

      {logsQ.loading && <LoadingState label="Loading admin audit trail..." />}
      {logsQ.error && <ErrorState error={logsQ.error} onRetry={logsQ.refetch} />}
      {!logsQ.loading && !logsQ.error && logsQ.data?.length === 0 && (
        <EmptyState title="No audit logs recorded yet" />
      )}

      {!logsQ.loading && !logsQ.error && logsQ.data?.length > 0 && (
        <section className="rr-card overflow-hidden">
          <div className="flex items-center gap-2 border-b border-rr-lavender/15 px-5 py-3.5">
            <FileText className="h-4 w-4 text-rr-gold" />
            <h2 className="text-sm font-bold text-rr-light">Recent Admin Events</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase text-rr-lavender">
                <tr>
                  <th className="px-4 py-2.5">Timestamp</th>
                  <th className="px-4 py-2.5">Actor</th>
                  <th className="px-4 py-2.5">Action</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {logsQ.data.map((row) => (
                  <tr key={row.id} className="hover:bg-rr-plum/40">
                    <td className="whitespace-nowrap px-4 py-2.5 text-rr-lavender">{fmtDateTime(row.createdAt)}</td>
                    <td className="px-4 py-2.5 font-mono text-rr-light">{row.actorEmail || 'System'}</td>
                    <td className="px-4 py-2.5 font-mono font-semibold text-rr-gold">{row.action}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                          row.status === 'SUCCESS' || row.status === 'PASS'
                            ? 'bg-rr-teal/15 text-rr-teal'
                            : 'bg-rr-coral/15 text-rr-coral'
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[11px] text-rr-lavender">
                      {row.detailsJson ? JSON.stringify(row.detailsJson) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 pb-4">
            <Pagination meta={logsQ.meta} onPageChange={setPage} />
          </div>
        </section>
      )}
    </div>
  );
}

