import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import {
  Area,
  AreaChart,
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
import { ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtInt, fmtNum } from '../utils/formatters.js';

export function PressurePage() {
  const [framework, setFramework] = useState('CHASE');
  const [format, setFormat] = useState('ALL');
  const [season, setSeason] = useState('ALL');
  const [pressureLevel, setPressureLevel] = useState('ALL');
  const [innings, setInnings] = useState('ALL');
  const [phase, setPhase] = useState('ALL');

  const filterParams = {
    format,
    season,
    pressureLevel,
    innings: innings === 'ALL' ? undefined : Number(innings),
    phase,
  };

  const summaryQ = useApiQuery(
    (signal) => api.getPressureSummary(filterParams, signal),
    [format, season, pressureLevel, innings, phase]
  );

  const distQ = useApiQuery(
    (signal) => api.getPressureDistribution({ ...filterParams, framework }, signal),
    [framework, format, season, pressureLevel, innings, phase]
  );

  const modelsQ = useApiQuery((signal) => api.getPressureModels({}, signal), []);

  const fwData = summaryQ.data?.frameworks || {};

  return (
    <div>
      <PageHeader
        eyebrow="Phase 4 · Pre-Delivery Pressure Intelligence"
        title="Match Pressure Analytics (Model C Primary)"
        subtitle="Three conceptually distinct 0–100 pre-delivery match-difficulty indices built strictly on pre-ball match state (zero outcome leakage)."
      />

      {/* Interactive Filters */}
      <div className="rr-card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
        {[
          { label: 'Active Framework', val: framework, set: setFramework, opts: [['CHASE', 'Chase (Inn 2)'], ['FIRST_INNINGS', 'First Innings (Inn 1)'], ['BOWLING', 'Bowling (Inn 1+2)'], ['BATTING_COMBINED', 'Batting Combined']] },
          { label: 'Competition', val: format, set: setFormat, opts: [['ALL', 'All (IPL + T20I)'], ['IPL', 'IPL'], ['T20I', 'T20I']] },
          { label: 'Season', val: season, set: setSeason, opts: [['ALL', '2022–2026'], ['2022', '2022'], ['2023', '2023'], ['2024', '2024'], ['2025', '2025'], ['2026', '2026']] },
          { label: 'Pressure Category', val: pressureLevel, set: setPressureLevel, opts: [['ALL', 'All Tiers'], ['LOW PRESSURE', 'LOW'], ['MODERATE PRESSURE', 'MODERATE'], ['HIGH PRESSURE', 'HIGH'], ['EXTREME PRESSURE', 'EXTREME'], ['UNAVAILABLE', 'UNAVAILABLE']] },
          { label: 'Innings', val: innings, set: setInnings, opts: [['ALL', 'Inn 1 & 2'], ['1', 'Innings 1'], ['2', 'Innings 2']] },
          { label: 'Match Phase', val: phase, set: setPhase, opts: [['ALL', 'All Phases'], ['Powerplay', 'Powerplay'], ['Middle', 'Middle'], ['Death', 'Death'], ['Unavailable', 'Unavailable']] },
        ].map((f) => (
          <label key={f.label} className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
            {f.label}
            <select
              value={f.val}
              onChange={(e) => f.set(e.target.value)}
              className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
            >
              {f.opts.map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
          </label>
        ))}
      </div>

      {summaryQ.loading && <LoadingState label="Aggregating pre-delivery pressure cube..." />}
      {summaryQ.error && <ErrorState error={summaryQ.error} onRetry={summaryQ.refetch} />}

      {/* Three Separate Pre-Delivery Context Framework Panels */}
      {summaryQ.data && (
        <>
          <div className="mb-6 grid gap-5 lg:grid-cols-3">
            {/* Chase Pressure */}
            <div className="rr-card border-t-2 border-t-rr-pink p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-rr-light">1. Chase Pressure (Inn 2)</h2>
                <span className="font-mono text-xs font-bold text-rr-pink">
                  Mean {fmtNum(fwData.CHASE?.meanPressureIndex, 1)}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-rr-lavender">Thresholds: &lt;32 LOW · 32–50 MOD · 50–74 HIGH · ≥74 EXT</p>
              <dl className="mt-4 grid grid-cols-2 gap-2.5 text-xs">
                {[
                  ['Required Run Rate', fmtNum(fwData.CHASE?.contextMetrics?.meanRequiredRunRate, 2)],
                  ['Current Run Rate', fmtNum(fwData.CHASE?.contextMetrics?.meanCurrentRunRate, 2)],
                  ['Mean Runs Remaining', fmtNum(fwData.CHASE?.contextMetrics?.meanRunsRemaining, 1)],
                  ['Legal Balls Remaining', fmtNum(fwData.CHASE?.contextMetrics?.meanLegalBallsRemaining, 1)],
                  ['Wickets Lost / In Hand', `${fmtNum(fwData.CHASE?.contextMetrics?.meanWicketsLost, 1)} / ${fmtNum(fwData.CHASE?.contextMetrics?.meanWicketsRemaining, 1)}`],
                  ['HIGH+EXT Share', fmtNum(fwData.CHASE?.highExtremeSharePct, 1, { suffix: '%' })],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-rr-plum/60 p-2.5">
                    <dt className="text-[10px] text-rr-lavender">{k}</dt>
                    <dd className="mt-0.5 font-mono font-semibold text-rr-light tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* First-Innings Pressure */}
            <div className="rr-card border-t-2 border-t-rr-gold p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-rr-light">2. First-Innings Pressure (Inn 1)</h2>
                <span className="font-mono text-xs font-bold text-rr-gold">
                  Mean {fmtNum(fwData.FIRST_INNINGS?.meanPressureIndex, 1)}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-rr-lavender">Thresholds: &lt;30 LOW · 30–45 MOD · 45–61 HIGH · ≥61 EXT</p>
              <dl className="mt-4 grid grid-cols-2 gap-2.5 text-xs">
                {[
                  ['Mean Current Score', fmtNum(fwData.FIRST_INNINGS?.contextMetrics?.meanCurrentScore, 1)],
                  ['Legal Balls Elapsed', fmtNum(fwData.FIRST_INNINGS?.contextMetrics?.meanLegalBallsElapsed, 1)],
                  ['Current Run Rate', fmtNum(fwData.FIRST_INNINGS?.contextMetrics?.meanCurrentRunRate, 2)],
                  ['Wickets Lost', fmtNum(fwData.FIRST_INNINGS?.contextMetrics?.meanWicketsLost, 2)],
                  ['Valid Deliveries', fmtInt(fwData.FIRST_INNINGS?.validPressureDeliveries)],
                  ['HIGH+EXT Share', fmtNum(fwData.FIRST_INNINGS?.highExtremeSharePct, 1, { suffix: '%' })],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-rr-plum/60 p-2.5">
                    <dt className="text-[10px] text-rr-lavender">{k}</dt>
                    <dd className="mt-0.5 font-mono font-semibold text-rr-light tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* Bowling Pressure */}
            <div className="rr-card border-t-2 border-t-rr-teal p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-rr-light">3. Bowling Pressure (Inn 1 + 2)</h2>
                <span className="font-mono text-xs font-bold text-rr-teal">
                  Mean {fmtNum(fwData.BOWLING?.meanPressureIndex, 1)}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-rr-lavender">Thresholds: &lt;47 LOW · 47–60 MOD · 60–68 HIGH · ≥68 EXT</p>
              <dl className="mt-4 grid grid-cols-2 gap-2.5 text-xs">
                {[
                  ['Opposition Score', fmtNum(fwData.BOWLING?.contextMetrics?.meanCurrentScore, 1)],
                  ['Opp Wickets in Hand', fmtNum(fwData.BOWLING?.contextMetrics?.meanWicketsRemaining, 2)],
                  ['Balls Remaining', fmtNum(fwData.BOWLING?.contextMetrics?.meanLegalBallsRemaining, 1)],
                  ['Mean Bowl Economy', fmtNum(fwData.BOWLING?.outcomes?.bowlingEconomy, 2)],
                  ['Valid Deliveries', fmtInt(fwData.BOWLING?.validPressureDeliveries)],
                  ['HIGH+EXT Share', fmtNum(fwData.BOWLING?.highExtremeSharePct, 1, { suffix: '%' })],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-rr-plum/60 p-2.5">
                    <dt className="text-[10px] text-rr-lavender">{k}</dt>
                    <dd className="mt-0.5 font-mono font-semibold text-rr-light tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>

          {/* UNAVAILABLE Missing Context Disclosure */}
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-rr-gold/35 bg-rr-gold/10 p-4 text-xs">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rr-gold" />
            <div>
              <div className="font-bold text-rr-gold">
                Missing-Context Policy — {fmtInt(fwData.BATTING_COMBINED?.unavailableDeliveries)} UNAVAILABLE Deliveries Preserved
              </div>
              <p className="mt-1 text-rr-light/90">{summaryQ.data.unavailablePolicy}</p>
            </div>
          </div>
        </>
      )}

      {/* Distribution Histogram & Tier Breakdown */}
      {distQ.data && (
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <ChartCard
            title={`0–100 Score Distribution (${framework.replace('_', ' ')})`}
            subtitle="Comparing Model C (Primary) against Model A (Fixed) and Model B (ECDF)"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={distQ.data.histogram} margin={{ top: 10, right: 12, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                  <XAxis dataKey="binLabel" tick={{ fill: '#B8A6C2', fontSize: 10 }} interval={2} />
                  <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="modelC" name="Model C (Primary)" stroke={RR_COLORS.pink} fill="rgba(232,62,128,0.28)" strokeWidth={2.5} />
                  <Area type="monotone" dataKey="modelA" name="Model A (Fixed)" stroke={RR_COLORS.gold} fill="rgba(216,180,90,0.08)" strokeWidth={1.5} />
                  <Area type="monotone" dataKey="modelB" name="Model B (ECDF)" stroke={RR_COLORS.blue} fill="rgba(124,158,242,0.08)" strokeWidth={1.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Exposure & Outcome Validation by Pressure Category"
            subtitle="UNAVAILABLE deliveries displayed separately with NULL pressure index"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={distQ.data.byLevel.map((r) => ({ ...r, label: r.pressureLevel.replace(' PRESSURE', '') }))}
                  margin={{ top: 10, right: 12, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(184,166,194,0.14)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#B8A6C2', fontSize: 11 }} />
                  <Tooltip contentStyle={RR_TOOLTIP_STYLE} />
                  <Bar dataKey="deliveries" name="Deliveries" fill={RR_COLORS.pink} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>
      )}

      {/* Model A vs B vs C Comparison Table */}
      {modelsQ.data && (
        <section className="rr-card overflow-hidden">
          <div className="border-b border-rr-lavender/15 px-5 py-3.5">
            <h2 className="text-base font-bold text-rr-light">Model Comparison — Models A, B &amp; C</h2>
            <p className="text-xs text-rr-lavender">
              Model C eliminates IPL vs. T20I Inn-1 scoring bias (~10x smaller IPL–T20I gap than Models A &amp; B) and is the verified primary framework.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase tracking-wider text-rr-lavender">
                <tr>
                  <th className="px-4 py-2.5">Framework</th>
                  <th className="px-4 py-2.5">Model</th>
                  <th className="px-4 py-2.5 text-right">Mean (SD)</th>
                  <th className="px-4 py-2.5 text-right">IPL Mean</th>
                  <th className="px-4 py-2.5 text-right">T20I Mean</th>
                  <th className="px-4 py-2.5 text-right">IPL − T20I</th>
                  <th className="px-4 py-2.5 text-right">Spearman vs C</th>
                  <th className="px-4 py-2.5 text-right">Top-30 Agree</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {modelsQ.data.modelComparison.map((m, i) => (
                  <tr
                    key={`${m.framework}-${m.model}-${i}`}
                    className={m.isPrimaryFramework ? 'bg-rr-pink/10 font-medium' : 'hover:bg-rr-plum/40'}
                  >
                    <td className="px-4 py-2.5 text-rr-light">{m.framework}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-rr-light">{m.model}</span>
                      {m.isPrimaryFramework && (
                        <span className="ml-2 inline-flex items-center gap-1 rounded bg-rr-pink px-1.5 py-0.5 text-[10px] font-bold text-white">
                          <CheckCircle2 className="h-3 w-3" /> PRIMARY
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                      {fmtNum(m.mean, 2)} ({fmtNum(m.std, 1)})
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(m.ipl_mean, 2)}</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(m.t20i_mean, 2)}</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(m.ipl_minus_t20i_mean, 2, { sign: true })}</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(m.spearman_corr_with_model_c, 3)}</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtNum(m.top30_agreement_with_c_pct, 1, { suffix: '%' })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

