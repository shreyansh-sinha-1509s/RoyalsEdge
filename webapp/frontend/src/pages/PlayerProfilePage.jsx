import { AlertTriangle, ArrowLeft, GitCompare, ShieldAlert, Trophy } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
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
import { KpiCard } from '../components/common/KpiCard.jsx';
import { ErrorState, LoadingState } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import {
  evidenceBadgeClasses,
  fmtCi,
  fmtNum,
  fmtReliability,
  humanizeEnum,
  stabilityBadgeClasses,
} from '../utils/formatters.js';

export function PlayerProfilePage() {
  const { playerId } = useParams();
  const [activeDisc, setActiveDisc] = useState(null);

  const profileQ = useApiQuery((signal) => api.getPlayerProfile(playerId, signal), [playerId]);
  const perfQ = useApiQuery((signal) => api.getPlayerPerformance(playerId, {}, signal), [playerId]);
  const relQ = useApiQuery((signal) => api.getPlayerReliability(playerId, {}, signal), [playerId]);
  const trendsQ = useApiQuery((signal) => api.getPlayerTrends(playerId, {}, signal), [playerId]);

  if (profileQ.loading) return <LoadingState label={`Loading profile for player_id=${playerId}...`} />;
  if (profileQ.error) return <ErrorState error={profileQ.error} onRetry={profileQ.refetch} />;
  if (!profileQ.data) return null;

  const { overview, rankings, explanations } = profileQ.data;
  const availableDiscs = overview.disciplines.length > 0 ? overview.disciplines : ['batting'];
  const disc = activeDisc && availableDiscs.includes(activeDisc) ? activeDisc : availableDiscs[0];

  const perfBlock = disc === 'batting' ? perfQ.data?.batting : perfQ.data?.bowling;
  const relBlock = disc === 'batting' ? relQ.data?.batting : relQ.data?.bowling;
  const ranking = disc === 'batting' ? rankings.batting : rankings.bowling;
  const explanation = disc === 'batting' ? explanations.batting : explanations.bowling;
  const rel = relBlock?.reliability;
  const summary = perfBlock?.summary;

  const breakdownData = (perfBlock?.pressureBreakdown || []).map((b) => ({
    level: b.pressureLevel.replace(' PRESSURE', ''),
    rate: b.primaryRate,
    netImpact: b.netImpactRate,
    balls: b.balls,
  }));

  const seasonData = (trendsQ.data?.seasonTrends || []).filter((s) => s.discipline === disc);
  const isInsufficientRel = rel?.reliabilityScore === null || rel?.reliabilityScore === undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/players" className="inline-flex items-center gap-1.5 text-xs font-semibold text-rr-lavender hover:text-rr-pink">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Player Explorer
        </Link>
        <Link
          to={`/compare?discipline=${disc}&playerIds=${overview.playerId}`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-rr-pink/40 bg-rr-pink/10 px-3 py-1.5 text-xs font-semibold text-rr-pink hover:bg-rr-pink hover:text-white"
        >
          <GitCompare className="h-3.5 w-3.5" /> Compare Player
        </Link>
      </div>

      {/* Player Identity Banner */}
      <section className="rr-card p-6">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-rr-plum px-2 py-0.5 font-mono text-xs font-bold text-rr-gold">
                player_id: {overview.playerId}
              </span>
              <span className="rounded-md border border-rr-lavender/25 px-2 py-0.5 text-[11px] font-semibold text-rr-lavender">
                {overview.competitionExposure}
              </span>
              {ranking?.isTop10 && (
                <span className="inline-flex items-center gap-1 rounded-md bg-rr-gold px-2 py-0.5 text-[11px] font-bold text-rr-plum">
                  <Trophy className="h-3 w-3" /> Official Top 10 (#{ranking.rank} {disc})
                </span>
              )}
              {overview.sharesNameWithOtherId && (
                <span className="inline-flex items-center gap-1 rounded-md bg-rr-pink/20 px-2 py-0.5 text-[11px] font-semibold text-rr-pink">
                  <AlertTriangle className="h-3 w-3" /> Shared Name — Strictly Keyed on ID {overview.playerId}
                </span>
              )}
            </div>

            <h1 className="mt-2 text-2xl font-extrabold text-rr-light sm:text-3xl">{overview.displayName}</h1>
            <p className="mt-1 text-xs text-rr-lavender">
              Role: <strong className="text-rr-light">{disc === 'batting' ? overview.battingRole || overview.inferredPlayingRole : overview.bowlingRole || overview.inferredPlayingRole}</strong>
              {' · '}Teams: <strong className="text-rr-light">{overview.teamNames || 'N/A'}</strong>
              {' · '}Seasons: <strong className="text-rr-light">{overview.seasonsRepresented?.join(', ') || 'N/A'}</strong>
            </p>
          </div>

          {availableDiscs.length > 1 && (
            <div className="flex rounded-lg border border-rr-lavender/20 bg-rr-plum p-1">
              {availableDiscs.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setActiveDisc(d)}
                  className={`rounded-md px-3.5 py-1.5 text-xs font-semibold capitalize transition ${
                    disc === d ? 'bg-rr-pink text-white' : 'text-rr-lavender hover:text-rr-light'
                  }`}
                >
                  {d} Profile
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Deterministic Data-Backed Explanation */}
        {explanation && (
          <div className="mt-5 rounded-xl border border-rr-lavender/15 bg-rr-plum/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-bold uppercase tracking-wider text-rr-gold">
                Data-Backed Analytical Summary
              </div>
              <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold ${evidenceBadgeClasses(explanation.status)}`}>
                {humanizeEnum(explanation.status)}
              </span>
            </div>
            <p className="mt-1.5 text-sm font-semibold text-rr-light">{explanation.headline}</p>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <div>
                <div className="text-[11px] font-semibold text-rr-teal">Measured Strengths</div>
                <ul className="mt-1 space-y-1 text-xs text-rr-lavender">
                  {explanation.strengths.length > 0
                    ? explanation.strengths.map((s, i) => <li key={i}>• {s}</li>)
                    : <li>• No pressure-tier strengths recorded.</li>}
                </ul>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-rr-coral">Limitations &amp; Uncertainty</div>
                <ul className="mt-1 space-y-1 text-xs text-rr-lavender">
                  {explanation.limitations.length > 0
                    ? explanation.limitations.map((l, i) => <li key={i}>• {l}</li>)
                    : <li>• Standard observational historical caveats apply.</li>}
                </ul>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* NULL Reliability Explicit Banner if Insufficient Evidence */}
      {isInsufficientRel && (
        <div className="flex items-start gap-3 rounded-xl border border-rr-coral/40 bg-rr-coral/10 p-4 text-xs">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rr-coral" />
          <div>
            <div className="font-bold text-rr-coral">Insufficient Evidence — Reliability Score is NULL (Never Imputed as 0)</div>
            <p className="mt-1 text-rr-light/90">
              {relQ.data?.nullPolicyNote || 'Fewer than 5 pressure innings or insufficient exposure to estimate cross-match reliability.'}
            </p>
          </div>
        </div>
      )}

      {/* Core Metric Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KpiCard
          label="Final Rank"
          value={ranking ? `#${ranking.rank}` : 'Unranked'}
          subtext={ranking ? `Score ${fmtNum(ranking.finalRankingScore, 2)} / 100` : 'Below primary cutoff'}
          accent={ranking?.isTop10 ? 'gold' : 'none'}
        />
        <KpiCard
          label={disc === 'batting' ? 'EB Impact (/100b)' : 'EB Impact (/24b)'}
          value={fmtNum(rel?.ebPressureImpact, disc === 'batting' ? 1 : 2, { sign: true })}
          subtext={`Raw ${fmtNum(rel?.rawPressureImpact, disc === 'batting' ? 1 : 2, { sign: true })}`}
          accent="pink"
        />
        <KpiCard
          label="Reliability (0–100)"
          value={isInsufficientRel ? 'NULL' : fmtNum(rel?.reliabilityScore, 1)}
          subtext={isInsufficientRel ? 'Insufficient Evidence' : 'Volume-free consistency'}
          accent="gold"
        />
        <KpiCard
          label="Evidence Strength"
          value={fmtNum(rel?.evidenceStrengthScore, 1)}
          subtext={`${rel?.pressureBalls ?? 0}b · ${rel?.pressureMatches ?? 0}m`}
          accent="teal"
        />
        <KpiCard
          label="95% Bootstrap CI"
          value={fmtCi(rel?.impactCi95Low, rel?.impactCi95High, disc === 'batting' ? 0 : 1)}
          subtext="Match-clustered (B=500)"
        />
        <KpiCard
          label="MC Top-10 Prob"
          value={ranking ? fmtNum(ranking.mcProbTop10Pct, 1, { suffix: '%' }) : 'N/A'}
          subtext={ranking ? `Methods: ${ranking.methodsInTop10OutOf8 ?? 'N/A'}/8` : 'Not in eligible pool'}
        />
      </div>

      {/* Charts: Pressure Tier Breakdown & Seasonal Trends */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard
          title={`Performance by Pressure Category (${disc})`}
          subtitle={disc === 'batting' ? 'Strike Rate & Net Impact (/100b) across Model C tiers' : 'Economy & Net Impact (/24b) across Model C tiers'}
        >
          {breakdownData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={breakdownData} margin={{ top: 10, right: 12, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                  <XAxis dataKey="level" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="rate" name={disc === 'batting' ? 'Strike Rate' : 'Economy'} fill={RR_COLORS.pink} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="netImpact" name="Net Impact" fill={RR_COLORS.teal} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-12 text-center text-xs text-rr-lavender">No pressure-category breakdown available.</p>
          )}
        </ChartCard>

        <ChartCard
          title={`Season-by-Season Pressure Trend (${disc})`}
          subtitle="HIGH + EXTREME pressure primary rate & net impact (2022–2026)"
        >
          {seasonData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={seasonData} margin={{ top: 10, right: 16, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                  <XAxis dataKey="seasonYear" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="primaryRate" name={disc === 'batting' ? 'Pressure SR' : 'Pressure Econ'} stroke={RR_COLORS.gold} strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="netImpactRate" name="Net Impact" stroke={RR_COLORS.teal} strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-12 text-center text-xs text-rr-lavender">No seasonal pressure exposure recorded.</p>
          )}
        </ChartCard>
      </div>

      {/* Detailed Context Splits & Reliability Components */}
      <div className="grid gap-6 lg:grid-cols-2">
        {summary && (
          <section className="rr-card p-5">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rr-gold">
              Context Splits — Format, Innings &amp; Phase (Under Pressure)
            </h2>
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
              {(disc === 'batting'
                ? [
                    ['IPL Pressure', `${summary.pressureIplBf}b · SR ${fmtNum(summary.pressureIplSr, 1)}`],
                    ['T20I Pressure', `${summary.pressureT20iBf}b · SR ${fmtNum(summary.pressureT20iSr, 1)}`],
                    ['Innings 1', `${summary.pressureInn1Bf}b · SR ${fmtNum(summary.pressureInn1Sr, 1)}`],
                    ['Chase (Inn 2)', `${summary.pressureChaseBf}b · SR ${fmtNum(summary.pressureChaseSr, 1)}`],
                    ['Powerplay', `${summary.pressurePowerplayBf}b · SR ${fmtNum(summary.pressurePowerplaySr, 1)}`],
                    ['Middle / Death', `${summary.pressureMiddleBf}b (${fmtNum(summary.pressureMiddleSr, 0)}) / ${summary.pressureDeathBf}b (${fmtNum(summary.pressureDeathSr, 0)})`],
                  ]
                : [
                    ['IPL Pressure', `${summary.pressureIplLb}b · Econ ${fmtNum(summary.pressureIplEcon, 2)}`],
                    ['T20I Pressure', `${summary.pressureT20iLb}b · Econ ${fmtNum(summary.pressureT20iEcon, 2)}`],
                    ['Innings 1', `${summary.pressureInn1Lb}b · Econ ${fmtNum(summary.pressureInn1Econ, 2)}`],
                    ['Innings 2', `${summary.pressureInn2Lb}b · Econ ${fmtNum(summary.pressureInn2Econ, 2)}`],
                    ['Powerplay', `${summary.pressurePowerplayLb}b · Econ ${fmtNum(summary.pressurePowerplayEcon, 2)}`],
                    ['Middle / Death', `${summary.pressureMiddleLb}b (${fmtNum(summary.pressureMiddleEcon, 1)}) / ${summary.pressureDeathLb}b (${fmtNum(summary.pressureDeathEcon, 1)})`],
                  ]
              ).map(([label, value]) => (
                <div key={label} className="rounded-lg bg-rr-plum/60 p-3">
                  <div className="text-[10px] uppercase text-rr-lavender">{label}</div>
                  <div className="mt-1 font-mono font-semibold text-rr-light">{value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="rr-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rr-gold">
              Reliability Sub-Components &amp; Robustness
            </h2>
            {ranking?.stabilityTier && (
              <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold ${stabilityBadgeClasses(ranking.stabilityTier)}`}>
                {humanizeEnum(ranking.stabilityTier)}
              </span>
            )}
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
            {[
              ['Reliability Score', fmtReliability(rel?.reliabilityScore)],
              ['Innings Stability (40%)', fmtNum(rel?.compInningsStability, 3)],
              ['Floor Consistency (30%)', fmtNum(rel?.compFloorConsistency, 3)],
              ['Cross-Condition (20%)', fmtNum(rel?.compCrossConditionStability, 3)],
              ['Seasonal Stability (10%)', fmtNum(rel?.compSeasonalStability, 3)],
              ['MC Rank 90% Interval', ranking ? `#${fmtNum(ranking.mcRankP05, 0)} – #${fmtNum(ranking.mcRankP95, 0)}` : 'N/A'],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg bg-rr-plum/60 p-3">
                <dt className="text-[10px] uppercase text-rr-lavender">{k}</dt>
                <dd className="mt-1 font-mono font-semibold text-rr-light">{v}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  );
}

