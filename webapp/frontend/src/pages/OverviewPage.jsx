import { Activity, Award, BarChart3, Layers, ShieldCheck, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartCard, RR_COLORS, RR_TOOLTIP_STYLE } from '../charts/ChartCard.jsx';
import { KpiCard } from '../components/common/KpiCard.jsx';
import { ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtInt, fmtNum, humanizeEnum, stabilityBadgeClasses } from '../utils/formatters.js';

export function OverviewPage() {
  const { data, loading, error, refetch } = useApiQuery((signal) => api.getOverview(signal), []);

  if (loading) return <LoadingState label="Loading RR PERFORMANCE LAB overview..." />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (!data) return null;

  const { snapshot, top10Batters, top10Bowlers, pressureLevels } = data;

  const batChartData = top10Batters.map((p) => ({
    name: p.playerName.split(' ').slice(-1)[0],
    fullName: p.playerName,
    score: Number(p.finalRankingScore.toFixed(2)),
    reliability: Number(p.reliabilityScore.toFixed(1)),
    evidence: Number(p.evidenceScore.toFixed(1)),
  }));

  const bowlChartData = top10Bowlers.map((p) => ({
    name: p.playerName.split(' ').slice(-1)[0],
    fullName: p.playerName,
    score: Number(p.finalRankingScore.toFixed(2)),
    reliability: Number(p.reliabilityScore.toFixed(1)),
    evidence: Number(p.evidenceScore.toFixed(1)),
  }));

  const levelChart = pressureLevels
    .filter((r) => r.framework === 'Batting Combined (Inn 1+2)' || r.framework === 'Bowling (Inn 1+2)')
    .reduce((acc, row) => {
      const lvl = row.pressure_level;
      let item = acc.find((x) => x.level === lvl);
      if (!item) {
        item = { level: lvl.replace(' PRESSURE', ''), batting: 0, bowling: 0 };
        acc.push(item);
      }
      if (row.framework.startsWith('Batting')) item.batting = Number(row.deliveries || 0);
      if (row.framework.startsWith('Bowling')) item.bowling = Number(row.deliveries || 0);
      return acc;
    }, []);

  return (
    <div>
      <PageHeader
        eyebrow="Overview Dashboard · IPL & T20I (2022–2026)"
        title="Performance Intelligence Overview"
        subtitle="Verified historical dataset snapshot, Model C pressure exposure distribution, and official Phase 6 Top 10 Batters & Bowlers shortlists."
        actions={
          <>
            <Link
              to="/batting"
              className="rounded-lg bg-rr-pink px-3.5 py-2 text-xs font-semibold text-white hover:bg-rr-pink/90"
            >
              Batting Rankings
            </Link>
            <Link
              to="/bowling"
              className="rounded-lg border border-rr-teal/40 bg-rr-teal/10 px-3.5 py-2 text-xs font-semibold text-rr-teal hover:bg-rr-teal/20"
            >
              Bowling Rankings
            </Link>
            <Link
              to="/compare"
              className="rounded-lg border border-rr-lavender/25 px-3.5 py-2 text-xs font-semibold text-rr-light hover:border-rr-gold hover:text-rr-gold"
            >
              Compare Players
            </Link>
          </>
        }
      />

      {/* Top KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KpiCard label="Verified Deliveries" value={fmtInt(snapshot.deliveries)} subtext="Regular IPL + T20I innings" accent="pink" icon={Activity} />
        <KpiCard label="Matches (Ball Data)" value={fmtInt(snapshot.matchesWithBallData)} subtext={`${fmtInt(snapshot.totalEligibleMatches)} eligible matches`} accent="gold" icon={Layers} />
        <KpiCard label="Reconciled Innings" value={fmtInt(snapshot.innings)} subtext="Zero scoring diffs" icon={BarChart3} />
        <KpiCard label="Batters Analyzed" value={fmtInt(snapshot.battersAnalyzed)} subtext={`${fmtInt(snapshot.eligibleBatters)} primary eligible`} accent="pink" icon={Users} />
        <KpiCard label="Bowlers Analyzed" value={fmtInt(snapshot.bowlersAnalyzed)} subtext={`${fmtInt(snapshot.eligibleBowlers)} primary eligible`} accent="teal" icon={ShieldCheck} />
        <KpiCard label="Total Player IDs" value={fmtInt(snapshot.totalPlayers)} subtext="Strictly keyed by player_id" icon={Award} />
      </div>

      {/* Interactive Overview Charts */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <ChartCard
          title="Top 10 Batters — Composite Score vs. Reliability"
          subtitle="Official Balanced Primary (50/25/15/10) ranking · IPL + T20I (2022–2026)"
          footer="Source: final_batting_rankings.csv reconciled against RR_Performance_Lab_Top_10_Batters.csv"
        >
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={batChartData} margin={{ top: 10, right: 12, left: -12, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="score" name="Final Score" fill={RR_COLORS.pink} radius={[4, 4, 0, 0]} />
                <Bar dataKey="reliability" name="Reliability" fill={RR_COLORS.gold} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Top 10 Bowlers — Composite Score vs. Reliability"
          subtitle="Official Balanced Primary (50/25/15/10) ranking · IPL + T20I (2022–2026)"
          footer="Source: final_bowling_rankings.csv reconciled against RR_Performance_Lab_Top_10_Bowlers.csv"
        >
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bowlChartData} margin={{ top: 10, right: 12, left: -12, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="score" name="Final Score" fill={RR_COLORS.teal} radius={[4, 4, 0, 0]} />
                <Bar dataKey="reliability" name="Reliability" fill={RR_COLORS.gold} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      {/* Pressure Tier Distribution + Key Analytical Insights */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <ChartCard
          title="Model C Delivery Exposure by Pressure Tier"
          subtitle="Explicitly includes 1,551 UNAVAILABLE deliveries (never folded into LOW)"
          className="lg:col-span-2"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={levelChart} margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                <XAxis dataKey="level" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="batting" name="Batting Deliveries" fill={RR_COLORS.pink} radius={[4, 4, 0, 0]} />
                <Bar dataKey="bowling" name="Bowling Deliveries" fill={RR_COLORS.blue} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <div className="rr-card flex flex-col justify-between p-5">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-rr-gold">Key Analytical Insights</h3>
            <ul className="mt-3 space-y-3 text-xs leading-relaxed text-rr-lavender">
              <li>
                <strong className="text-rr-light">Format Calibration:</strong> Model C removes IPL&apos;s +0.55 to +0.88 RPO scoring advantage in Inn 1 (~10x lower format bias than fixed-par Model A).
              </li>
              <li>
                <strong className="text-rr-light">Empirical Bayes Shrinkage:</strong> Prior strength <span className="font-mono text-rr-light">k = 8.65</span> matches (batting) and <span className="font-mono text-rr-light">k = 30.00</span> matches (bowling) prevents small-sample outliers from dominating.
              </li>
              <li>
                <strong className="text-rr-light">Honest Caveats:</strong> Moderate-sample bowlers (Nasum Ahmed 93b, Mark Wood 100b, Joshua Little 115b) carry wider 95% CIs than high-exposure pillars (Axar Patel 749b, Rashid Khan 810b).
              </li>
            </ul>
          </div>
          <Link
            to="/methodology"
            className="mt-4 inline-block text-xs font-semibold text-rr-pink hover:underline"
          >
            Inspect Full Methodology & Robustness →
          </Link>
        </div>
      </div>

      {/* Compact Top 10 Side-by-Side Preview Tables */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {[
          { title: 'Official Top 10 Batters', rows: top10Batters, to: '/batting', isBat: true },
          { title: 'Official Top 10 Bowlers', rows: top10Bowlers, to: '/bowling', isBat: false },
        ].map((block) => (
          <div key={block.title} className="rr-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-rr-lavender/15 px-5 py-3.5">
              <h3 className="text-sm font-bold text-rr-light">{block.title}</h3>
              <Link to={block.to} className="text-xs font-semibold text-rr-pink hover:underline">
                Full Table & Filters →
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-rr-plum/70 text-[11px] uppercase tracking-wider text-rr-lavender">
                  <tr>
                    <th className="px-4 py-2.5">Rk</th>
                    <th className="px-4 py-2.5">Player (ID)</th>
                    <th className="px-4 py-2.5 text-right">Score</th>
                    <th className="px-4 py-2.5 text-right">{block.isBat ? 'EB/100b' : 'EB/24b'}</th>
                    <th className="px-4 py-2.5 text-right">Rel</th>
                    <th className="px-4 py-2.5">Stability</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rr-lavender/10">
                  {block.rows.map((r) => (
                    <tr key={r.playerId} className="transition hover:bg-rr-pink/5">
                      <td className="px-4 py-2.5 font-mono font-bold text-rr-gold">#{r.rank}</td>
                      <td className="px-4 py-2.5">
                        <Link to={`/players/${r.playerId}`} className="font-semibold text-rr-light hover:text-rr-pink">
                          {r.playerName}
                        </Link>
                        <span className="ml-1.5 font-mono text-[10px] text-rr-lavender">#{r.playerId}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono font-bold tabular-nums">{fmtNum(r.finalRankingScore, 2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-rr-teal tabular-nums">
                        {fmtNum(r.ebPressureImpact, block.isBat ? 1 : 2, { sign: true })}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(r.reliabilityScore, 1)}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold ${stabilityBadgeClasses(r.stabilityTier)}`}>
                          {humanizeEnum(r.stabilityTier)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

