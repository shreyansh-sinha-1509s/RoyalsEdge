import { Calendar, Search } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Pagination } from '../components/common/Pagination.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtDate, fmtNum, humanizeEnum } from '../utils/formatters.js';

export function MatchesPage() {
  const [search, setSearch] = useState('');
  const [format, setFormat] = useState('ALL');
  const [season, setSeason] = useState('ALL');
  const [completionType, setCompletionType] = useState('ALL');
  const [minPressure, setMinPressure] = useState('');
  const [sortBy, setSortBy] = useState('matchDate');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);

  const matchesQ = useApiQuery(
    (signal) =>
      api.getMatches(
        {
          search: search.trim() || undefined,
          format,
          season,
          completionType,
          minPressure: minPressure !== '' ? Number(minPressure) : undefined,
          sortBy,
          sortOrder,
          page,
          limit: 20,
        },
        signal
      ),
    [search, format, season, completionType, minPressure, sortBy, sortOrder, page]
  );

  return (
    <div>
      <PageHeader
        eyebrow="Historical Archive · Server-Side Paginated (Zero Live Scores)"
        title="Match & Performance Explorer"
        subtitle="Explore all 853 eligible IPL & T20I matches (2022–2026) with reconciled innings totals, DLS classifications, and Model C pressure summaries."
      />

      {/* Filters */}
      <div className="rr-card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender lg:col-span-2">
          Search Team, Series, Country or Match ID
          <div className="relative mt-1">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-rr-lavender" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="e.g., Rajasthan Royals, India, 21586..."
              className="w-full rounded-lg border border-rr-lavender/25 bg-rr-plum py-1.5 pl-8 pr-3 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
            />
          </div>
        </label>

        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Format
          <select
            value={format}
            onChange={(e) => { setFormat(e.target.value); setPage(1); }}
            className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light"
          >
            <option value="ALL">All (IPL + T20I)</option>
            <option value="IPL">IPL</option>
            <option value="T20I">T20I</option>
          </select>
        </label>

        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Season
          <select
            value={season}
            onChange={(e) => { setSeason(e.target.value); setPage(1); }}
            className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light"
          >
            {['ALL', '2022', '2023', '2024', '2025', '2026'].map((s) => (
              <option key={s} value={s}>{s === 'ALL' ? '2022–2026' : s}</option>
            ))}
          </select>
        </label>

        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Min Mean Pressure
          <select
            value={minPressure}
            onChange={(e) => { setMinPressure(e.target.value); setPage(1); }}
            className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light"
          >
            <option value="">Any Pressure</option>
            <option value="50">&gt;= 50 (High)</option>
            <option value="65">&gt;= 65 (Very High)</option>
          </select>
        </label>

        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Sort By
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split(':');
              setSortBy(sb);
              setSortOrder(so);
              setPage(1);
            }}
            className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light"
          >
            <option value="matchDate:desc">Newest First</option>
            <option value="matchDate:asc">Oldest First</option>
            <option value="meanChasePressure:desc">Highest Chase Pressure</option>
            <option value="meanI1Pressure:desc">Highest Inn 1 Pressure</option>
            <option value="meanBowlingPressure:desc">Highest Bowling Pressure</option>
          </select>
        </label>
      </div>

      {matchesQ.loading && <LoadingState label="Loading historical matches..." />}
      {matchesQ.error && <ErrorState error={matchesQ.error} onRetry={matchesQ.refetch} />}
      {!matchesQ.loading && !matchesQ.error && matchesQ.data?.length === 0 && (
        <EmptyState
          title="No matches found"
          action={
            <button
              type="button"
              onClick={() => { setSearch(''); setFormat('ALL'); setSeason('ALL'); setCompletionType('ALL'); setMinPressure(''); setPage(1); }}
              className="rounded-lg bg-rr-pink px-3.5 py-1.5 text-xs font-semibold text-white"
            >
              Reset Filters
            </button>
          }
        />
      )}

      {!matchesQ.loading && !matchesQ.error && matchesQ.data?.length > 0 && (
        <div className="rr-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase tracking-wider text-rr-lavender">
                <tr>
                  <th className="px-4 py-3">Date / ID</th>
                  <th className="px-4 py-3">Fixture &amp; Competition</th>
                  <th className="px-4 py-3">Format</th>
                  <th className="px-4 py-3">Scorecard</th>
                  <th className="px-4 py-3 text-right">Inn 1 Press</th>
                  <th className="px-4 py-3 text-right">Chase Press</th>
                  <th className="px-4 py-3 text-right">Bowl Press</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {matchesQ.data.map((m) => (
                  <tr key={m.matchId} className="transition hover:bg-rr-pink/5">
                    <td className="whitespace-nowrap px-4 py-2.5">
                      <div className="flex items-center gap-1 font-medium text-rr-light">
                        <Calendar className="h-3 w-3 text-rr-lavender" />
                        {fmtDate(m.matchDate)}
                      </div>
                      <div className="font-mono text-[10px] text-rr-gold">Match #{m.matchId}</div>
                    </td>
                    <td className="px-4 py-2.5">
                      <Link to={`/matches/${m.matchId}`} className="font-semibold text-rr-light hover:text-rr-pink">
                        {m.homeTeam} vs {m.awayTeam}
                      </Link>
                      <div className="text-[11px] text-rr-lavender">
                        {m.compName} {m.result ? `· ${m.result}` : ''}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="rounded bg-rr-plum px-2 py-0.5 font-mono text-[10px] font-semibold text-rr-light">
                        {m.matchFormat} {m.season}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[11px] tabular-nums">
                      {m.hasBallData ? (
                        <>
                          <div>Inn 1: {m.inn1TotalRuns ?? '—'}/{m.inn1Wickets ?? '—'}</div>
                          <div className="text-rr-lavender">Inn 2: {m.inn2TotalRuns ?? '—'}/{m.inn2Wickets ?? '—'}</div>
                        </>
                      ) : (
                        <span className="text-rr-lavender/70">No ball data</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(m.meanI1Pressure, 1)}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-rr-pink tabular-nums">{fmtNum(m.meanChasePressure, 1)}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-rr-teal tabular-nums">{fmtNum(m.meanBowlingPressure, 1)}</td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-[10px] text-rr-lavender">
                      {humanizeEnum(m.matchCompletionClassification)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 pb-4">
            <Pagination meta={matchesQ.meta} onPageChange={setPage} />
          </div>
        </div>
      )}
    </div>
  );
}

