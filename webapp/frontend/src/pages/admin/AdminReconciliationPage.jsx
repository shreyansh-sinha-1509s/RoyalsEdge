import { CheckCircle2, Play, XCircle } from 'lucide-react';
import { useState } from 'react';
import { LoadingState, PageHeader } from '../../components/common/States.jsx';
import { api } from '../../services/api.js';
import { fmtDateTime, fmtInt } from '../../utils/formatters.js';

export function AdminReconciliationPage() {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const runCheck = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.adminReconcile();
      setReport(res.data);
    } catch (err) {
      setError(err.message || 'Reconciliation failed.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Phase 6 Official Submission Authority Check"
        title="Data Reconciliation"
        subtitle="Verify byte-level consistency between PostgreSQL Top 10 Batters & Bowlers, row counts, NULL reliability rules, shared player IDs, and official submission/*.csv files."
        actions={
          <button
            type="button"
            disabled={running}
            onClick={runCheck}
            className="inline-flex items-center gap-2 rounded-lg bg-rr-teal px-4 py-2 text-xs font-bold text-rr-plum hover:bg-rr-teal/90 disabled:opacity-60"
          >
            <Play className="h-3.5 w-3.5" />
            {running ? 'Running Reconciliation...' : 'Run Reconciliation Check'}
          </button>
        }
      />

      {running && <LoadingState label="Comparing PostgreSQL tables against official submission CSVs..." />}

      {error && (
        <div className="rounded-xl border border-rr-coral/40 bg-rr-coral/10 p-4 text-xs text-rr-coral" role="alert">
          {error}
        </div>
      )}

      {!report && !running && !error && (
        <div className="rr-card p-8 text-center text-sm text-rr-lavender">
          Click <strong className="text-rr-light">Run Reconciliation Check</strong> above to execute a live consistency verification against{' '}
          <code className="text-rr-gold">submission/RR_Performance_Lab_Top_10_Batters.csv</code> and{' '}
          <code className="text-rr-gold">submission/RR_Performance_Lab_Top_10_Bowlers.csv</code>.
        </div>
      )}

      {report && (
        <div className="space-y-5">
          <div
            className={`flex items-center justify-between rounded-xl border p-5 ${
              report.passed
                ? 'border-rr-teal/40 bg-rr-teal/10 text-rr-teal'
                : 'border-rr-coral/40 bg-rr-coral/10 text-rr-coral'
            }`}
          >
            <div className="flex items-center gap-3">
              {report.passed ? <CheckCircle2 className="h-6 w-6" /> : <XCircle className="h-6 w-6" />}
              <div>
                <div className="text-base font-extrabold">
                  {report.passed ? 'RECONCILIATION PASSED — EXACT MATCH' : 'RECONCILIATION FAILED'}
                </div>
                <div className="text-xs opacity-90">Checked at {fmtDateTime(report.checkedAt)}</div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Batting Top 10 vs CSV', report.battingTop10Check?.exactMatch],
              ['Bowling Top 10 vs CSV', report.bowlingTop10Check?.exactMatch],
              ['NULL Reliability Preserved', report.nullReliabilityPreserved],
              ['Shared Player IDs Preserved', report.sharedPlayerIdsPreserved],
            ].map(([label, ok]) => (
              <div key={label} className="rr-card p-4">
                <div className="text-[11px] text-rr-lavender">{label}</div>
                <div className={`mt-1 font-mono text-base font-bold ${ok ? 'text-rr-teal' : 'text-rr-coral'}`}>
                  {ok ? 'PASS' : 'FAIL'}
                </div>
              </div>
            ))}
          </div>

          {report.counts && (
            <section className="rr-card p-5">
              <h3 className="text-sm font-bold text-rr-gold">Verified Row Counts</h3>
              <div className="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
                {Object.entries(report.counts).map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-rr-plum/60 p-2.5">
                    <div className="text-[10px] text-rr-lavender">{k}</div>
                    <div className="font-mono text-sm font-bold text-rr-light">{fmtInt(v)}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {report.discrepancies?.length > 0 && (
            <section className="rr-card border-rr-coral/40 p-5">
              <h3 className="text-sm font-bold text-rr-coral">Discrepancies Found ({report.discrepancies.length})</h3>
              <ul className="mt-2 space-y-1 text-xs text-rr-light">
                {report.discrepancies.map((d, i) => (
                  <li key={i}>• {d}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

