import { AlertTriangle, Plus, Search, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartCard, RR_COLORS, RR_TOOLTIP_STYLE } from '../charts/ChartCard.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtCi, fmtNum, fmtReliability, humanizeEnum } from '../utils/formatters.js';

const SERIES_COLORS = [RR_COLORS.pink, RR_COLORS.gold, RR_COLORS.teal, RR_COLORS.blue];

const DEFAULT_BAT_IDS = [796, 37052, 152]; // Matthew Wade, Naman Dhir, Ravindra Jadeja
const DEFAULT_BOWL_IDS = [4658, 2876, 4722]; // Nasum Ahmed, Axar Patel, Rashid Khan

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialDisc = searchParams.get('discipline') === 'bowling' ? 'bowling' : 'batting';
  const initialIds = (searchParams.get('playerIds') || '')
    .split(',')
    .map((x) => Number(x.trim()))
    .filter((n) => Number.isInteger(n) && n > 0)
    .slice(0, 4);

  const [discipline, setDiscipline] = useState(initialDisc);
  const [selectedIds, setSelectedIds] = useState(
    initialIds.length >= 2 ? initialIds : initialIds.length === 1 ? [initialIds[0], initialDisc === 'batting' ? 152 : 2876].filter((v, i, a) => a.indexOf(v) === i) : initialDisc === 'batting' ? DEFAULT_BAT_IDS : DEFAULT_BOWL_IDS
  );
  const [pickerQuery, setPickerQuery] = useState('');
  const [pickerResults, setPickerResults] = useState([]);

  useEffect(() => {
    setSearchParams({ discipline, playerIds: selectedIds.join(',') }, { replace: true });
  }, [discipline, selectedIds, setSearchParams]);

  useEffect(() => {
    if (pickerQuery.trim().length < 2) {
      setPickerResults([]);
      return undefined;
    }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const res = await api.getPlayers({ discipline, search: pickerQuery.trim(), limit: 8 }, ctrl.signal);
        setPickerResults((res.data || []).filter((p) => !selectedIds.includes(p.playerId)));
      } catch {
        setPickerResults([]);
      }
    }, 200);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [pickerQuery, discipline, selectedIds]);

  const compareQ = useApiQuery(
    (signal) => api.comparePlayers(discipline, selectedIds, signal),
    [discipline, selectedIds.join(',')],
    { enabled: selectedIds.length >= 2 }
  );

  const switchDiscipline = (nextDisc) => {
    if (nextDisc === discipline) return;
    setDiscipline(nextDisc);
    setSelectedIds(nextDisc === 'batting' ? DEFAULT_BAT_IDS : DEFAULT_BOWL_IDS);
    setPickerQuery('');
    setPickerResults([]);
  };

  const addPlayer = (id) => {
    if (selectedIds.includes(id) || selectedIds.length >= 4) return;
    setSelectedIds((prev) => [...prev, id]);
    setPickerQuery('');
    setPickerResults([]);
  };

  const removePlayer = (id) => {
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  };

  const players = compareQ.data?.players || [];

  const pillarBarData = players.map((p) => ({
    name: `${p.displayName.split(' ').slice(-1)[0]} (#${p.playerId})`,
    Performance: p.reliability?.performanceScore ?? 0,
    Reliability: p.reliability?.reliabilityScore ?? 0,
    Evidence: p.reliability?.evidenceStrengthScore ?? 0,
  }));

  // Combine seasons 2022–2026 across selected players
  const allYears = [2022, 2023, 2024, 2025, 2026];
  const seasonChartData = allYears.map((yr) => {
    const row = { year: yr };
    players.forEach((p) => {
      const s = (p.seasonTrends || []).find((x) => x.seasonYear === yr);
      row[`p_${p.playerId}`] = s?.primaryRate ?? null;
    });
    return row;
  });

  return (
    <div>
      <PageHeader
        eyebrow="Side-by-Side Analytics · Same-Discipline Enforcement"
        title="Compare Players Under Pressure"
        subtitle="Compare 2 to 4 players strictly within the same discipline (Batter vs. Batter or Bowler vs. Bowler). Never compares incompatible metrics or fabricates missing values."
        actions={
          <div className="flex rounded-lg border border-rr-lavender/20 bg-rr-surface p-1">
            {['batting', 'bowling'].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => switchDiscipline(d)}
                className={`rounded-md px-3.5 py-1.5 text-xs font-semibold capitalize transition ${
                  discipline === d ? 'bg-rr-pink text-white' : 'text-rr-lavender hover:text-rr-light'
                }`}
              >
                {d} Comparison
              </button>
            ))}
          </div>
        }
      />

      {/* Player Selection Bar */}
      <div className="rr-card mb-6 p-4">
        <div className="flex flex-wrap items-center gap-2">
          {selectedIds.map((id, idx) => {
            const pObj = players.find((x) => x.playerId === id);
            return (
              <span
                key={id}
                className="inline-flex items-center gap-2 rounded-lg border border-rr-lavender/25 bg-rr-plum px-3 py-1.5 text-xs font-semibold text-rr-light"
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SERIES_COLORS[idx % SERIES_COLORS.length] }} />
                {pObj ? pObj.displayName : `Player ${id}`}
                <span className="font-mono text-[10px] text-rr-gold">ID {id}</span>
                <button
                  type="button"
                  aria-label={`Remove player ${id}`}
                  onClick={() => removePlayer(id)}
                  className="text-rr-lavender hover:text-rr-coral"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            );
          })}

          {selectedIds.length < 4 && (
            <div className="relative min-w-[240px] flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-rr-lavender" />
              <input
                type="text"
                value={pickerQuery}
                onChange={(e) => setPickerQuery(e.target.value)}
                placeholder={`Add ${discipline} player (max 4) by name or ID...`}
                className="w-full rounded-lg border border-rr-lavender/25 bg-rr-plum py-1.5 pl-8 pr-3 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
              />
              {pickerResults.length > 0 && (
                <div className="absolute left-0 right-0 z-20 mt-1 rounded-lg border border-rr-lavender/25 bg-rr-surface p-1 shadow-rr">
                  {pickerResults.map((p) => (
                    <button
                      key={p.playerId}
                      type="button"
                      onClick={() => addPlayer(p.playerId)}
                      className="flex w-full items-center justify-between rounded px-2.5 py-2 text-left text-xs hover:bg-rr-plum/70"
                    >
                      <span>
                        <strong className="text-rr-light">{p.displayName}</strong>{' '}
                        <span className="font-mono text-[10px] text-rr-gold">ID {p.playerId}</span>
                      </span>
                      <Plus className="h-3.5 w-3.5 text-rr-pink" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {selectedIds.length < 2 && (
        <EmptyState
          title="Select at least 2 players to compare"
          description="Use the search bar above to add 2 to 4 players from the same discipline."
        />
      )}

      {selectedIds.length >= 2 && compareQ.loading && <LoadingState label="Loading side-by-side comparison..." />}
      {selectedIds.length >= 2 && compareQ.error && <ErrorState error={compareQ.error} onRetry={compareQ.refetch} />}

      {selectedIds.length >= 2 && compareQ.data && (
        <div className="space-y-6">
          {/* Sample Size Discrepancy Warning */}
          {compareQ.data.sampleSizeWarning && (
            <div className="flex items-start gap-3 rounded-xl border border-rr-gold/40 bg-rr-gold/10 p-4 text-xs">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rr-gold" />
              <div>
                <div className="font-bold text-rr-gold">Sample-Size Discrepancy Notice</div>
                <p className="mt-1 text-rr-light/90">{compareQ.data.sampleSizeWarning}</p>
              </div>
            </div>
          )}

          {/* Side-by-Side Metrics Table */}
          <section className="rr-card overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase tracking-wider text-rr-lavender">
                <tr>
                  <th className="px-4 py-3">Metric</th>
                  {players.map((p, idx) => (
                    <th key={p.playerId} className="px-4 py-3">
                      <Link to={`/players/${p.playerId}`} className="flex items-center gap-1.5 text-rr-light hover:text-rr-pink">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: SERIES_COLORS[idx % SERIES_COLORS.length] }} />
                        <span>{p.displayName}</span>
                      </Link>
                      <div className="font-mono text-[10px] font-normal text-rr-gold">
                        ID {p.playerId} {p.smallerSampleFlag ? '· Smaller Sample' : ''}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10 font-mono tabular-nums">
                {[
                  ['Role', (p) => p.role],
                  ['Final Rank', (p) => (p.ranking ? `#${p.ranking.rank}` : 'Unranked')],
                  ['Composite Score', (p) => fmtNum(p.ranking?.finalRankingScore, 2)],
                  [discipline === 'batting' ? 'EB Impact (/100b)' : 'EB Impact (/24b)', (p) => fmtNum(p.reliability?.ebPressureImpact, discipline === 'batting' ? 1 : 2, { sign: true })],
                  [discipline === 'batting' ? 'Pressure SR / Avg' : 'Pressure Econ / Wkts', (p) =>
                    discipline === 'batting'
                      ? `${fmtNum(p.performance.pressureStrikeRate, 1)} / ${fmtNum(p.performance.pressureAverage, 1)}`
                      : `${fmtNum(p.performance.pressureEconomy, 2)} / ${p.performance.pressureWickets}w`
                  ],
                  ['Reliability (0–100)', (p) => fmtReliability(p.reliability?.reliabilityScore)],
                  ['Evidence Strength', (p) => fmtNum(p.reliability?.evidenceStrengthScore, 1)],
                  ['Pressure Exposure', (p) => `${p.pressureBalls}b / ${p.performance.pressureMatches}m`],
                  ['95% Bootstrap CI', (p) => fmtCi(p.reliability?.impactCi95Low, p.reliability?.impactCi95High, discipline === 'batting' ? 0 : 1)],
                  ['MC Top-10 Prob', (p) => (p.ranking ? fmtNum(p.ranking.mcProbTop10Pct, 1, { suffix: '%' }) : 'N/A')],
                  ['Stability Tier', (p) => humanizeEnum(p.ranking?.stabilityTier || p.reliability?.evidenceTier)],
                ].map(([label, getter]) => (
                  <tr key={label} className="hover:bg-rr-plum/40">
                    <td className="px-4 py-2.5 font-sans font-semibold text-rr-lavender">{label}</td>
                    {players.map((p) => (
                      <td key={`${label}-${p.playerId}`} className="px-4 py-2.5 text-rr-light">
                        {getter(p)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Charts */}
          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard
              title="Three-Pillar Score Profile (0–100)"
              subtitle="Performance vs. Reliability vs. Evidence Strength (NULL reliability renders as empty)"
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={pillarBarData} margin={{ top: 10, right: 12, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                    <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Performance" fill={RR_COLORS.pink} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Reliability" fill={RR_COLORS.gold} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Evidence" fill={RR_COLORS.teal} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title={`Seasonal Pressure ${discipline === 'batting' ? 'Strike Rate' : 'Economy'} Trajectory`}
              subtitle="Only seasons with actual pressure exposure are plotted (no interpolated points)"
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={seasonChartData} margin={{ top: 10, right: 16, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                    <XAxis dataKey="year" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                    <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {players.map((p, idx) => (
                      <Line
                        key={p.playerId}
                        type="monotone"
                        dataKey={`p_${p.playerId}`}
                        name={p.displayName}
                        stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                        strokeWidth={2.5}
                        connectNulls={false}
                        dot={{ r: 4 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>
        </div>
      )}
    </div>
  );
}

