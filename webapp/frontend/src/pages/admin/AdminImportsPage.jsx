import { AlertTriangle, Database, Play } from 'lucide-react';
import { useState } from 'react';
import { Pagination } from '../../components/common/Pagination.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../../components/common/States.jsx';
import { useApiQuery } from '../../hooks/useApiQuery.js';
import { api } from '../../services/api.js';
import { fmtDateTime, fmtInt } from '../../utils/formatters.js';

export function AdminImportsPage() {
  const [page, setPage] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);

  const importsQ = useApiQuery((signal) => api.adminImports({ page, limit: 15 }, signal), [page]);

  const executeImport = async () => {
    setConfirmOpen(false);
    setRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const res = await api.adminRunImport();
      setRunResult(res.data);
      importsQ.refetch();
    } catch (err) {
      setRunError(err.message || 'Analytics import failed.');
      importsQ.refetch();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Protected Data Pipeline Operations"
        title="Data Import & Management"
        subtitle="Trigger transactional, idempotent re-imports strictly from verified Phase 2–6 Python CSV outputs with automatic post-import reconciliation."
        actions={
          <button
            type="button"
            disabled={running}
            onClick={() => setConfirmOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-rr-pink px-4 py-2 text-xs font-bold text-white shadow-rr-pink hover:bg-rr-pink/90 disabled:opacity-60"
          >
            <Play className="h-3.5 w-3.5" />
            {running ? 'Running Verified Import...' : 'Run Analytics Import'}
          </button>
        }
      />

      {running && <LoadingState label="Streaming 193,988 deliveries & replacing analytical tables inside PostgreSQL transaction..." />}

      {runError && (
        <div className="rounded-xl border border-rr-coral/40 bg-rr-coral/10 p-4 text-xs text-rr-coral" role="alert">
          <strong>Import Error:</strong> {runError}
        </div>
      )}

      {runResult && (
        <div className="rounded-xl border border-rr-teal/40 bg-rr-teal/10 p-4 text-xs">
          <div className="font-bold text-rr-teal">
            Import Succeeded — Batch {runResult.batchId} ({runResult.durationMs} ms)
          </div>
          <p className="mt-1 text-rr-light/90">
            Inserted {fmtInt(runResult.insertedCount)} database records · Reconciliation:{' '}
            <strong>{runResult.reconcileReport?.passed ? 'EXACT MATCH PASS' : 'FAIL'}</strong>
          </p>
        </div>
      )}

      {/* Confirmation Modal */}
      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
          <div className="rr-card w-full max-w-md p-6 shadow-rr">
            <div className="flex items-center gap-2 text-rr-gold">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="text-base font-bold text-rr-light">Confirm Transactional Re-Import</h3>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-rr-lavender">
              This will atomically refresh all 16 analytical PostgreSQL tables from verified Python CSVs in{' '}
              <code className="text-rr-light">data/processed/</code>, <code className="text-rr-light">outputs/</code>, and{' '}
              <code className="text-rr-light">submission/</code>, then run Top-10 reconciliation. Admin accounts and audit logs
              are preserved. If any validation fails, the transaction rolls back safely.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                className="rounded-lg border border-rr-lavender/25 px-4 py-2 text-xs font-semibold text-rr-lavender hover:text-rr-light"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeImport}
                className="rounded-lg bg-rr-pink px-4 py-2 text-xs font-bold text-white hover:bg-rr-pink/90"
              >
                Confirm &amp; Run Import
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Logs Table */}
      <section className="rr-card overflow-hidden">
        <div className="flex items-center gap-2 border-b border-rr-lavender/15 px-5 py-3.5">
          <Database className="h-4 w-4 text-rr-pink" />
          <h2 className="text-sm font-bold text-rr-light">Import Execution History</h2>
        </div>

        {importsQ.loading && <div className="p-6"><LoadingState label="Loading import history..." /></div>}
        {importsQ.error && <div className="p-6"><ErrorState error={importsQ.error} onRetry={importsQ.refetch} /></div>}
        {!importsQ.loading && !importsQ.error && importsQ.data?.length === 0 && (
          <div className="p-6"><EmptyState title="No imports recorded yet" description="Run npm run import:data or trigger a verified import above." /></div>
        )}

        {!importsQ.loading && !importsQ.error && importsQ.data?.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase text-rr-lavender">
                <tr>
                  <th className="px-4 py-2.5">Batch ID</th>
                  <th className="px-4 py-2.5">Trigger</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5 text-right">Inserted</th>
                  <th className="px-4 py-2.5">Reconcile</th>
                  <th className="px-4 py-2.5 text-right">Duration</th>
                  <th className="px-4 py-2.5">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {importsQ.data.map((log) => (
                  <tr key={log.id} className="hover:bg-rr-plum/40">
                    <td className="px-4 py-2.5 font-mono text-rr-gold">{log.batchId}</td>
                    <td className="px-4 py-2.5 text-rr-lavender">{log.triggeredBy}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                          log.status === 'SUCCESS'
                            ? 'bg-rr-teal/15 text-rr-teal'
                            : log.status === 'STARTED'
                              ? 'bg-rr-gold/15 text-rr-gold'
                              : 'bg-rr-coral/15 text-rr-coral'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtInt(log.insertedCount)}</td>
                    <td className="px-4 py-2.5 font-mono">
                      {log.reconcilePassed === true ? (
                        <span className="text-rr-teal">PASS</span>
                      ) : log.reconcilePassed === false ? (
                        <span className="text-rr-coral">FAIL</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">{log.durationMs ? `${log.durationMs} ms` : '—'}</td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-rr-lavender">{fmtDateTime(log.startedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 pb-4">
              <Pagination meta={importsQ.meta} onPageChange={setPage} />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

