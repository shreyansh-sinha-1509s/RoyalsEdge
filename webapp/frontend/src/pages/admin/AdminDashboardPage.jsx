import { CheckCircle2, Database, RefreshCw, Server } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { KpiCard } from '../../components/common/KpiCard.jsx';
import { ErrorState, LoadingState, PageHeader } from '../../components/common/States.jsx';
import { useApiQuery } from '../../hooks/useApiQuery.js';
import { api } from '../../services/api.js';
import { fmtInt } from '../../utils/formatters.js';

export function AdminDashboardPage() {
  const healthQ = useApiQuery((signal) => api.adminHealth(signal), []);
  const [cacheMsg, setCacheMsg] = useState(null);
  const [clearing, setClearing] = useState(false);

  const handleCacheRefresh = async () => {
    setClearing(true);
    setCacheMsg(null);
    try {
      const res = await api.adminRefreshCache();
      setCacheMsg(`Cache refreshed (${res.data?.clearedKeys ?? 0} keys cleared).`);
      healthQ.refetch();
    } catch (err) {
      setCacheMsg(`Error: ${err.message}`);
    } finally {
      setClearing(false);
    }
  };

  if (healthQ.loading) return <LoadingState label="Checking backend & Neon database health..." />;
  if (healthQ.error) return <ErrorState error={healthQ.error} onRetry={healthQ.refetch} />;
  if (!healthQ.data) return null;

  const h = healthQ.data;
  const counts = h.tableCounts || {};

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Protected Admin Console"
        title="System & Database Overview"
        subtitle="Live operational telemetry exposed by /api/admin/health. Secrets and database credentials are never exposed."
        actions={
          <button
            type="button"
            disabled={clearing}
            onClick={handleCacheRefresh}
            className="inline-flex items-center gap-2 rounded-lg border border-rr-gold/40 bg-rr-gold/10 px-3.5 py-2 text-xs font-semibold text-rr-gold hover:bg-rr-gold hover:text-rr-plum disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${clearing ? 'animate-spin' : ''}`} />
            Refresh Server Cache
          </button>
        }
      />

      {cacheMsg && (
        <div className="rounded-lg border border-rr-teal/35 bg-rr-teal/10 px-4 py-2.5 text-xs text-rr-teal">
          {cacheMsg}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Database Status" value={h.database?.toUpperCase() || 'OK'} subtext={`Status: ${h.status}`} accent="teal" icon={Database} />
        <KpiCard label="Server Uptime" value={`${fmtInt(h.uptimeSeconds)}s`} subtext={`RSS Memory: ${h.memoryMb} MB`} icon={Server} />
        <KpiCard label="Cache Hits / Entries" value={`${h.cache?.hits ?? 0} / ${h.cache?.entries ?? 0}`} subtext={`Misses: ${h.cache?.misses ?? 0}`} accent="gold" />
        <KpiCard label="Import Runs Logged" value={fmtInt(counts.importLogsCount)} subtext={h.importInProgress ? 'Import running...' : 'Idle'} accent="pink" />
      </div>

      {/* Table Row Counts */}
      <section className="rr-card p-5">
        <h2 className="text-sm font-bold uppercase tracking-wider text-rr-gold">PostgreSQL Imported Record Counts</h2>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Object.entries(counts).map(([table, count]) => (
            <div key={table} className="rounded-lg bg-rr-plum/60 p-3">
              <div className="text-[11px] text-rr-lavender">{table}</div>
              <div className="mt-1 font-mono text-lg font-bold text-rr-light tabular-nums">{fmtInt(count)}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Source Directory Readiness & Quick Links */}
      <div className="grid gap-5 md:grid-cols-2">
        <section className="rr-card p-5">
          <h3 className="text-sm font-bold text-rr-light">Verified Python Source Directories</h3>
          <ul className="mt-3 space-y-2 text-xs">
            {[
              ['data/processed/', h.sourceDirectories?.dataProcessedAvailable],
              ['outputs/', h.sourceDirectories?.outputsAvailable],
              ['submission/', h.sourceDirectories?.submissionAvailable],
            ].map(([label, ok]) => (
              <li key={label} className="flex items-center justify-between rounded-lg bg-rr-plum/60 px-3 py-2">
                <span className="font-mono text-rr-light">{label}</span>
                <span className={ok ? 'inline-flex items-center gap-1 font-semibold text-rr-teal' : 'font-semibold text-rr-coral'}>
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {ok ? 'Readable' : 'Missing'}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="rr-card flex flex-col justify-between p-5">
          <div>
            <h3 className="text-sm font-bold text-rr-light">Operational Actions</h3>
            <p className="mt-1 text-xs text-rr-lavender">
              Manage validated CSV imports, verify Top-10 submission reconciliation, or inspect audit trails.
            </p>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/admin/imports" className="rounded-lg bg-rr-pink px-3.5 py-2 text-xs font-semibold text-white">
              Manage Imports
            </Link>
            <Link to="/admin/reconciliation" className="rounded-lg border border-rr-teal/40 bg-rr-teal/10 px-3.5 py-2 text-xs font-semibold text-rr-teal">
              Run Reconciliation
            </Link>
            <Link to="/admin/audit" className="rounded-lg border border-rr-lavender/25 px-3.5 py-2 text-xs font-semibold text-rr-light">
              View Audit Logs
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}

