import { ArrowLeft, Calendar, MapPin } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { KpiCard } from '../components/common/KpiCard.jsx';
import { ErrorState, LoadingState } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtDate, fmtNum, humanizeEnum } from '../utils/formatters.js';

export function MatchDetailPage() {
  const { matchId } = useParams();
  const matchQ = useApiQuery((signal) => api.getMatchDetail(matchId, signal), [matchId]);

  if (matchQ.loading) return <LoadingState label={`Loading match #${matchId}...`} />;
  if (matchQ.error) return <ErrorState error={matchQ.error} onRetry={matchQ.refetch} />;
  if (!matchQ.data) return null;

  const m = matchQ.data;

  return (
    <div className="space-y-6">
      <Link to="/matches" className="inline-flex items-center gap-1.5 text-xs font-semibold text-rr-lavender hover:text-rr-pink">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Match Explorer
      </Link>

      <section className="rr-card p-6">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded bg-rr-plum px-2 py-0.5 font-mono font-bold text-rr-gold">
            match_id: {m.matchId}
          </span>
          <span className="rounded border border-rr-lavender/25 px-2 py-0.5 text-rr-lavender">
            {m.matchFormat} · {m.season}
          </span>
          {m.isDlsMatch && (
            <span className="rounded bg-rr-gold/15 px-2 py-0.5 font-semibold text-rr-gold">DLS Match</span>
          )}
          <span className="rounded bg-rr-plum/70 px-2 py-0.5 text-[11px] text-rr-lavender">
            {m.historicalNotice}
          </span>
        </div>

        <h1 className="mt-3 text-2xl font-extrabold text-rr-light sm:text-3xl">
          {m.homeTeam} vs {m.awayTeam}
        </h1>
        <p className="mt-1 text-sm text-rr-lavender">{m.compName}</p>
        {m.result && <p className="mt-2 text-sm font-semibold text-rr-teal">{m.result}</p>}

        <div className="mt-4 flex flex-wrap gap-4 text-xs text-rr-lavender">
          <span className="inline-flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" /> {fmtDate(m.matchDate)}
          </span>
          {m.venueCountry && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" /> {m.venueCountry}
            </span>
          )}
          <span>Completion: <strong className="text-rr-light">{humanizeEnum(m.matchCompletionClassification)}</strong></span>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Mean Inn 1 Pressure" value={fmtNum(m.meanI1Pressure, 1)} subtext={`Max ${fmtNum(m.maxI1Pressure, 1)}`} accent="gold" />
        <KpiCard label="Mean Chase Pressure" value={fmtNum(m.meanChasePressure, 1)} subtext={`Max ${fmtNum(m.maxChasePressure, 1)}`} accent="pink" />
        <KpiCard label="Mean Bowling Pressure" value={fmtNum(m.meanBowlingPressure, 1)} subtext={`Max ${fmtNum(m.maxBowlingPressure, 1)}`} accent="teal" />
        <KpiCard label="High/Ext Balls (Bat/Bowl)" value={`${m.highOrExtremeBattingBalls ?? '—'} / ${m.highOrExtremeBowlingBalls ?? '—'}`} subtext={`${m.regularDeliveries} regular balls`} />
      </div>

      {/* Innings Cards */}
      <div className="grid gap-6 lg:grid-cols-2">
        {(m.innings || []).length === 0 ? (
          <div className="rr-card p-6 text-sm text-rr-lavender lg:col-span-2">
            No regular-innings ball-by-ball records exist for this match (e.g., abandoned match).
          </div>
        ) : (
          m.innings.map((inn) => (
            <section key={inn.innings} className="rr-card p-5">
              <div className="flex items-center justify-between border-b border-rr-lavender/15 pb-3">
                <div>
                  <span className="font-mono text-[11px] font-bold uppercase text-rr-pink">
                    Innings {inn.innings} ({inn.innings === 1 ? 'Setting Target' : 'Chase'})
                  </span>
                  <h2 className="text-base font-bold text-rr-light">
                    {inn.battingTeamName || `Team #${inn.battingTeamId}`} vs {inn.bowlingTeamName || `Team #${inn.bowlingTeamId}`}
                  </h2>
                </div>
                <div className="text-right font-mono">
                  <div className="text-xl font-extrabold text-rr-gold">
                    {inn.totalRuns}/{inn.wickets}
                  </div>
                  <div className="text-[11px] text-rr-lavender">
                    {Math.floor(inn.legalDeliveries / 6)}.{inn.legalDeliveries % 6} overs ({inn.legalDeliveries} LB)
                  </div>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
                {[
                  ['Batter Runs / Extras', `${inn.batterRuns} / ${inn.extrasTotalRuns}`],
                  ['Bowler Wkts / Run-Outs', `${inn.bowlerWickets} / ${inn.runOuts}`],
                  ['Wides / No-Balls', `${inn.wides} / ${inn.overstepNoballs + inn.otherNoballs}`],
                  ['Mean Batting Pressure', fmtNum(inn.meanBattingPressure, 1)],
                  ['Max Batting Pressure', fmtNum(inn.maxBattingPressure, 1)],
                  ['High/Ext Bat Balls', `${inn.highOrExtremeBattingBalls} (${inn.extremeBattingBalls} ext)`],
                  ['Mean Bowling Pressure', fmtNum(inn.meanBowlingPressure, 1)],
                  ['Max Bowling Pressure', fmtNum(inn.maxBowlingPressure, 1)],
                  ['High/Ext Bowl Balls', `${inn.highOrExtremeBowlingBalls} (${inn.extremeBowlingBalls} ext)`],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-rr-plum/60 p-2.5">
                    <dt className="text-[10px] text-rr-lavender">{k}</dt>
                    <dd className="mt-0.5 font-mono font-semibold text-rr-light">{v}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))
        )}
      </div>
    </div>
  );
}

