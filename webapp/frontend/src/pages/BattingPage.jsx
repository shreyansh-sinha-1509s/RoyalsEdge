import { ArrowUpDown, Search, Trophy } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import { ChartCard, RR_COLORS, RR_TOOLTIP_STYLE } from '../charts/ChartCard.jsx';
import { KpiCard } from '../components/common/KpiCard.jsx';
import { Pagination } from '../components/common/Pagination.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtCi, fmtInt, fmtNum, humanizeEnum, stabilityBadgeClasses } from '../utils/formatters.js';

const ROLES = ['ALL', 'Opener', 'Top-Order', 'Middle-Order', 'Finisher / Lower-Middle'];

export function BattingPage() {
  const [top10Only, setTop10Only] = useState(true);
  const [search, setSearch] = useState('');
  const [format, setFormat] = useState('ALL');
  const [season, setSeason] = useState('ALL');
  const [phase, setPhase] = useState('ALL');
  const [role, setRole] = useState('ALL');
  const [competition, setCompetition] = useState('ALL');
  const [stabilityTier, setStabilityTier] = useState('ALL');
  const [sortBy, setSortBy] = useState('rank');
  const [sortOrder, setSortOrder] = useState('asc');
  const [page, setPage] = useState(1);

  const summaryQ = useApiQuery(
    (signal) => api.getBattingSummary({ format, season, phase, role }, signal),
    [format, season, phase, role]
  );

  const rankingsQ = useApiQuery(
    (signal) =>
      api.getBattingRankings(
        {
          top10Only: top10Only ? 'true' : undefined,
          search: search.trim() || undefined,
          role,
          competition,
          stabilityTier,
          sortBy,
          sortOrder,
          page,
          limit: top10Only ? 10 : 20,
        },
        signal
      ),
    [top10Only, search, role, competition, stabilityTier, sortBy, sortOrder, page]
  );

  const toggleSort = (col) => {
    if (sortBy === col) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(col);
      setSortOrder(col === 'rank' ? 'asc' : 'desc');
    }
    setPage(1);
  };

  const kpis = summaryQ.data?.kpis;
  const scatter = summaryQ.data?.performanceVsReliabilityScatter || [];
  const byTier = (summaryQ.data?.byPressureCategory || []).map((t) => ({
    ...t,
    label: t.pressureLevel.replace(' PRESSURE', ''),
  }));
  const seasons = summaryQ.data?.seasonalTrends || [];
  const pVsNp = summaryQ.data?.pressureVsNonPressure;

  return (
    <div>
      <PageHeader
        eyebrow="Batting Analytics & Official Phase 6 Rankings"
        title="Batting Under Pressure"
        subtitle="Context-adjusted RVAE + wicket survival shrunk via Empirical Bayes (k = 8.65 matches), paired with volume-free reliability and match-clustered 95% CIs."
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => { setTop10Only(true); setPage(1); }}
              className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                top10Only
                  ? 'bg-rr-pink text-white shadow-rr-pink'
                  : 'border border-rr-lavender/25 text-rr-lavender hover:text-rr-light'
              }`}
            >
              <Trophy className="mr-1.5 inline h-3.5 w-3.5" />
              Official Top 10
            </button>
            <button
              type="button"
              onClick={() => { setTop10Only(false); setPage(1); }}
              className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                !top10Only
                  ? 'bg-rr-pink text-white shadow-rr-pink'
                  : 'border border-rr-lavender/25 text-rr-lavender hover:text-rr-light'
              }`}
            >
              All 173 Eligible
            </button>
          </div>
        }
      />

      {/* Interactive Analytics Filters */}
      <div className="rr-card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Search Player
          <div className="relative mt-1">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-rr-lavender" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Name, role, team..."
              className="w-full rounded-lg border border-rr-lavender/25 bg-rr-plum py-1.5 pl-8 pr-3 text-xs text-rr-light placeholder:text-rr-lavender/60 focus:border-rr-pink focus:outline-none"
            />
          </div>
        </label>

        {[
          { label: 'Format (Charts)', val: format, set: setFormat, opts: ['ALL', 'IPL', 'T20I'] },
          { label: 'Season (Charts)', val: season, set: setSeason, opts: ['ALL', '2022', '2023', '2024', '2025', '2026'] },
          { label: 'Match Phase', val: phase, set: setPhase, opts: ['ALL', 'Powerplay', 'Middle', 'Death'] },
          { label: 'Batting Role', val: role, set: setRole, opts: ROLES },
          { label: 'Stability Tier', val: stabilityTier, set: setStabilityTier, opts: ['ALL', 'CORE_CONSENSUS', 'MODERATELY_STABLE', 'ASSUMPTION_SENSITIVE'] },
        ].map((f) => (
          <label key={f.label} className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
            {f.label}
            <select
              value={f.val}
              onChange={(e) => { f.set(e.target.value); setPage(1); }}
              className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
            >
              {f.opts.map((o) => (
                <option key={o} value={o}>{o === 'ALL' ? 'All' : humanizeEnum(o)}</option>
              ))}
            </select>
          </label>
        ))}
      </div>

      {/* KPI Strip */}
      {summaryQ.loading && <LoadingState label="Loading batting pressure analytics..." />}
      {summaryQ.error && <ErrorState error={summaryQ.error} onRetry={summaryQ.refetch} />}
      {kpis && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <KpiCard label="Batters Analyzed" value={fmtInt(kpis.battersAnalyzed)} subtext=">=1 valid ball faced" accent="pink" />
          <KpiCard label="Primary Eligible" value={fmtInt(kpis.eligibleBatters)} subtext=">=80 BF & >=10 inn/m" accent="gold" />
          <KpiCard label="Pressure Runs" value={fmtInt(kpis.totalPressureRuns)} subtext="HIGH + EXTREME tiers" />
          <KpiCard label="Pressure Balls" value={fmtInt(kpis.totalPressureBallsFaced)} subtext="Verified batter BF" />
          <KpiCard label="Median Press SR" value={fmtNum(kpis.medianPressureStrikeRate, 1)} subtext="Eligible cohort" accent="teal" />
          <KpiCard label="High/Ext Exposures" value={fmtInt(kpis.highExtremeExposures)} subtext="Filtered cube balls" />
        </div>
      )}

      {/* Official Rankings Table */}
      <section className="rr-card mb-6 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rr-lavender/15 px-5 py-3.5">
          <div>
            <h2 className="text-base font-bold text-rr-light">
              {top10Only ? 'Official Ordered Top 10 Batters Under Pressure' : 'Full Eligible Batting Rankings (173 Players)'}
            </h2>
            <p className="text-xs text-rr-lavender">
              Balanced Primary Score (50% EB Performance · 25% Reliability · 15% Extreme & Lift · 10% Evidence). Click headers to sort.
            </p>
          </div>
          <select
            aria-label="Filter competition context"
            value={competition}
            onChange={(e) => { setCompetition(e.target.value); setPage(1); }}
            className="rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
          >
            {['ALL', 'IPL + T20I', 'IPL Only', 'T20I Only'].map((c) => (
              <option key={c} value={c}>{c === 'ALL' ? 'All Competitions' : c}</option>
            ))}
          </select>
        </div>

        {rankingsQ.loading && <div className="p-6"><LoadingState label="Loading verified batting rankings..." /></div>}
        {rankingsQ.error && <div className="p-6"><ErrorState error={rankingsQ.error} onRetry={rankingsQ.refetch} /></div>}
        {!rankingsQ.loading && !rankingsQ.error && rankingsQ.data?.length === 0 && (
          <div className="p-6"><EmptyState title="No batters match active filters" /></div>
        )}

        {!rankingsQ.loading && !rankingsQ.error && rankingsQ.data?.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase tracking-wider text-rr-lavender">
                <tr>
                  {[
                    ['rank', 'Rk'],
                    [null, 'Player (ID)'],
                    [null, 'Role'],
                    ['finalRankingScore', 'Score'],
                    ['ebPressureImpact', 'EB / 100b'],
                    ['pressureStrikeRate', 'Press SR'],
                    ['pressureAverage', 'Avg'],
                    ['reliabilityScore', 'Rel'],
                    ['evidenceScore', 'Evid'],
                    ['pressureBallsFaced', 'Exposure'],
                    [null, '95% CI'],
                    ['mcProbTop10Pct', 'MC Top10'],
                    [null, 'Stability'],
                  ].map(([col, label]) => (
                    <th key={label} className="whitespace-nowrap px-3.5 py-3">
                      {col ? (
                        <button
                          type="button"
                          onClick={() => toggleSort(col)}
                          className="inline-flex items-center gap-1 hover:text-rr-pink"
                        >
                          {label}
                          <ArrowUpDown className="h-3 w-3 opacity-60" />
                        </button>
                      ) : (
                        label
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {rankingsQ.data.map((r) => (
                  <tr key={r.playerId} className="transition hover:bg-rr-pink/5">
                    <td className="px-3.5 py-2.5 font-mono font-bold text-rr-gold">#{r.rank}</td>
                    <td className="whitespace-nowrap px-3.5 py-2.5">
                      <Link to={`/players/${r.playerId}`} className="font-semibold text-rr-light hover:text-rr-pink">
                        {r.playerName}
                      </Link>
                      <span className="ml-1.5 font-mono text-[10px] text-rr-lavender">ID {r.playerId}</span>
                      <div className="text-[10px] text-rr-lavender">{r.competitionContext}</div>
                    </td>
                    <td className="px-3.5 py-2.5 text-rr-lavender">{r.role}</td>
                    <td className="px-3.5 py-2.5 font-mono font-bold text-rr-light tabular-nums">
                      {fmtNum(r.finalRankingScore, 2)}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-rr-teal tabular-nums">
                      {fmtNum(r.ebPressureImpact, 1, { sign: true })}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums">{fmtNum(r.pressureStrikeRate, 1)}</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums">{fmtNum(r.pressureAverage, 1)}</td>
                    <td className="px-3.5 py-2.5 font-mono text-rr-gold tabular-nums">{fmtNum(r.reliabilityScore, 1)}</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums">{fmtNum(r.evidenceScore, 1)}</td>
                    <td className="whitespace-nowrap px-3.5 py-2.5 font-mono tabular-nums">
                      {r.pressureBallsFaced}b / {r.uniqueMatches}m
                    </td>
                    <td className="whitespace-nowrap px-3.5 py-2.5 font-mono text-[11px] text-rr-lavender tabular-nums">
                      {fmtCi(r.impactCi95Low, r.impactCi95High, 0)}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums">{fmtNum(r.mcProbTop10Pct, 0, { suffix: '%' })}</td>
                    <td className="whitespace-nowrap px-3.5 py-2.5">
                      <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold ${stabilityBadgeClasses(r.stabilityTier)}`}>
                        {r.stabilityTier ? humanizeEnum(r.stabilityTier) : humanizeEnum(r.evidenceTier)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 pb-4">
              <Pagination meta={rankingsQ.meta} onPageChange={setPage} />
            </div>
          </div>
        )}
      </section>

      {/* Analytical Charts */}
      {summaryQ.data && (
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard
            title="Strike Rate & Boundary / Dot % by Pressure Tier"
            subtitle="Aggregated server-side across selected format, season, and phase filters"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byTier} margin={{ top: 10, right: 12, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="strikeRate" name="Strike Rate" fill={RR_COLORS.pink} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="dotBallPct" name="Dot Ball %" fill={RR_COLORS.lavender} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="boundaryPct" name="Boundary %" fill={RR_COLORS.gold} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Performance vs. Reliability Separation (Eligible Cohort)"
            subtitle="Top 10 highlighted in Royals Pink · Volume-free reliability decoupled from raw balls"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 16, left: -10, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" />
                  <XAxis type="number" dataKey="performanceScore" name="Performance" domain={[0, 100]} tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <YAxis type="number" dataKey="reliabilityScore" name="Reliability" domain={[0, 85]} tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <ZAxis type="number" dataKey="pressureBallsFaced" range={[30, 160]} name="Balls Faced" />
                  <Tooltip
                    cursor={{ strokeDasharray: '3 3' }}
                    contentStyle={RR_TOOLTIP_STYLE}
                    formatter={(val, name) => [typeof val === 'number' ? val.toFixed(1) : val, name]}
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.playerName || ''}
                  />
                  <Scatter name="Eligible Batters" data={scatter}>
                    {scatter.map((entry) => (
                      <Cell
                        key={entry.playerId}
                        fill={entry.isTop10 ? RR_COLORS.pink : 'rgba(184,166,194,0.45)'}
                        stroke={entry.isTop10 ? '#FFFFFF' : 'none'}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Seasonal Pressure Strike Rate Trend (2022–2026)"
            subtitle="Aggregate HIGH + EXTREME batting strike rate across seasons"
          >
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={seasons} margin={{ top: 10, right: 16, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                  <XAxis dataKey="seasonYear" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <YAxis domain={['auto', 'auto']} tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="strikeRate" name="Pressure SR" stroke={RR_COLORS.pink} strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="average" name="Pressure Avg" stroke={RR_COLORS.gold} strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {pVsNp && (
            <ChartCard
              title="Pressure vs. Non-Pressure Cohort Comparison"
              subtitle={`Median eligible batter metrics (n = ${pVsNp.eligiblePlayers}) · Observational split`}
            >
              <div className="grid grid-cols-3 gap-3 pt-2">
                {[
                  { label: 'Median Strike Rate', p: pVsNp.medianPressureSr, np: pVsNp.medianNonPressureSr },
                  { label: 'Median Boundary %', p: pVsNp.medianPressureBoundaryPct, np: pVsNp.medianNonPressureBoundaryPct },
                  { label: 'Median Dot Ball %', p: pVsNp.medianPressureDotPct, np: pVsNp.medianNonPressureDotPct },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg border border-rr-lavender/15 bg-rr-plum/60 p-3.5">
                    <div className="text-[11px] font-semibold text-rr-lavender">{m.label}</div>
                    <div className="mt-2 font-mono text-lg font-bold text-rr-pink tabular-nums">{fmtNum(m.p, 1)}</div>
                    <div className="text-[10px] text-rr-lavender">Under Pressure</div>
                    <div className="mt-2 border-t border-rr-lavender/10 pt-2 font-mono text-sm text-rr-light tabular-nums">
                      {fmtNum(m.np, 1)}
                    </div>
                    <div className="text-[10px] text-rr-lavender">Non-Pressure</div>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}
        </div>
      )}
    </div>
  );
}

