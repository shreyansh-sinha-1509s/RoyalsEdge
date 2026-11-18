import { Search, Users } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Pagination } from '../components/common/Pagination.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { evidenceBadgeClasses, fmtNum, humanizeEnum } from '../utils/formatters.js';

export function PlayersPage() {
  const [discipline, setDiscipline] = useState('all');
  const [search, setSearch] = useState('');
  const [competition, setCompetition] = useState('ALL');
  const [evidenceTier, setEvidenceTier] = useState('ALL');
  const [eligibleOnly, setEligibleOnly] = useState(false);
  const [page, setPage] = useState(1);

  const playersQ = useApiQuery(
    (signal) =>
      api.getPlayers(
        {
          discipline,
          search: search.trim() || undefined,
          competition,
          evidenceTier,
          eligibleOnly: eligibleOnly ? 'true' : undefined,
          page,
          limit: 24,
        },
        signal
      ),
    [discipline, search, competition, evidenceTier, eligibleOnly, page]
  );

  return (
    <div>
      <PageHeader
        eyebrow="Player Directory · Strict Integer player_id Identity"
        title="Player Explorer"
        subtitle="Browse all 1,217 IPL & T20I players (2022–2026). Shared-name players are strictly separated by unique player_id and never merged."
        actions={
          <div className="flex items-center gap-1 rounded-lg border border-rr-lavender/20 bg-rr-surface p-1">
            {[
              ['all', 'All Players'],
              ['batting', 'Batters (824)'],
              ['bowling', 'Bowlers (596)'],
            ].map(([val, label]) => (
              <button
                key={val}
                type="button"
                onClick={() => { setDiscipline(val); setPage(1); }}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                  discipline === val ? 'bg-rr-pink text-white' : 'text-rr-lavender hover:text-rr-light'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        }
      />

      {/* Filter Bar */}
      <div className="rr-card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Search Name, Team or ID
          <div className="relative mt-1">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-rr-lavender" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="e.g., Rashid Khan or 4722..."
              className="w-full rounded-lg border border-rr-lavender/25 bg-rr-plum py-1.5 pl-8 pr-3 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
            />
          </div>
        </label>

        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Competition
          <select
            value={competition}
            onChange={(e) => { setCompetition(e.target.value); setPage(1); }}
            className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
          >
            <option value="ALL">All (IPL + T20I)</option>
            <option value="IPL">IPL</option>
            <option value="T20I">T20I</option>
          </select>
        </label>

        <label className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
          Evidence Tier
          <select
            value={evidenceTier}
            onChange={(e) => { setEvidenceTier(e.target.value); setPage(1); }}
            className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-2.5 py-1.5 text-xs text-rr-light focus:border-rr-pink focus:outline-none"
          >
            {['ALL', 'HIGH_CONFIDENCE', 'MODERATE_CONFIDENCE', 'LOW_EVIDENCE', 'INSUFFICIENT_EVIDENCE'].map((t) => (
              <option key={t} value={t}>{t === 'ALL' ? 'All Tiers' : humanizeEnum(t)}</option>
            ))}
          </select>
        </label>

        <div className="flex items-end">
          <label className="flex w-full cursor-pointer items-center gap-2 rounded-lg border border-rr-lavender/25 bg-rr-plum px-3 py-2 text-xs text-rr-light">
            <input
              type="checkbox"
              checked={eligibleOnly}
              onChange={(e) => { setEligibleOnly(e.target.checked); setPage(1); }}
              className="accent-rr-pink"
            />
            Primary-Eligible Ranked Only
          </label>
        </div>
      </div>

      {playersQ.loading && <LoadingState label="Searching player directory..." />}
      {playersQ.error && <ErrorState error={playersQ.error} onRetry={playersQ.refetch} />}
      {!playersQ.loading && !playersQ.error && playersQ.data?.length === 0 && (
        <EmptyState title="No players found" />
      )}

      {!playersQ.loading && !playersQ.error && playersQ.data?.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {playersQ.data.map((p) => {
              const batRel = p.battingReliability;
              const bowlRel = p.bowlingReliability;
              return (
                <Link
                  key={p.playerId}
                  to={`/players/${p.playerId}`}
                  className="rr-card flex flex-col justify-between p-4 transition hover:border-rr-pink"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <h3 className="text-sm font-bold text-rr-light">{p.displayName}</h3>
                          <span className="rounded bg-rr-plum px-1.5 py-0.5 font-mono text-[10px] text-rr-gold">
                            ID {p.playerId}
                          </span>
                          {p.sharesNameWithOtherId && (
                            <span className="rounded bg-rr-pink/20 px-1.5 py-0.5 text-[10px] font-semibold text-rr-pink">
                              Shared Name
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-[11px] text-rr-lavender">
                          {p.inferredPlayingRole || 'Player'} · {p.inIpl && p.inT20i ? 'IPL + T20I' : p.inIpl ? 'IPL' : p.inT20i ? 'T20I' : 'Excluded'}
                        </p>
                      </div>
                      <Users className="h-4 w-4 shrink-0 text-rr-lavender/60" />
                    </div>

                    {p.teamNames && (
                      <p className="mt-2 line-clamp-1 text-[11px] text-rr-lavender/80">{p.teamNames}</p>
                    )}

                    <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                      <div className="rounded-lg bg-rr-plum/60 p-2">
                        <div className="text-[10px] uppercase text-rr-lavender">Batting</div>
                        {p.battingPerformance ? (
                          <>
                            <div className="font-mono font-semibold text-rr-light">
                              {p.battingRanking ? `Rank #${p.battingRanking.rank}` : `SR ${fmtNum(p.battingPerformance.pressureStrikeRate, 1)}`}
                            </div>
                            <div className="font-mono text-[10px] text-rr-lavender">
                              {p.battingPerformance.pressureBallsFaced}b · Rel{' '}
                              {batRel?.reliabilityScore === null || batRel?.reliabilityScore === undefined
                                ? 'NULL'
                                : fmtNum(batRel.reliabilityScore, 1)}
                            </div>
                          </>
                        ) : (
                          <div className="text-rr-lavender/60">No data</div>
                        )}
                      </div>

                      <div className="rounded-lg bg-rr-plum/60 p-2">
                        <div className="text-[10px] uppercase text-rr-lavender">Bowling</div>
                        {p.bowlingPerformance ? (
                          <>
                            <div className="font-mono font-semibold text-rr-light">
                              {p.bowlingRanking ? `Rank #${p.bowlingRanking.rank}` : `Econ ${fmtNum(p.bowlingPerformance.pressureEconomy, 2)}`}
                            </div>
                            <div className="font-mono text-[10px] text-rr-lavender">
                              {p.bowlingPerformance.pressureLegalBalls}b · Rel{' '}
                              {bowlRel?.reliabilityScore === null || bowlRel?.reliabilityScore === undefined
                                ? 'NULL'
                                : fmtNum(bowlRel.reliabilityScore, 1)}
                            </div>
                          </>
                        ) : (
                          <div className="text-rr-lavender/60">No data</div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-rr-lavender/10 pt-2.5 text-[10px]">
                    <span className={`rounded border px-1.5 py-0.5 font-semibold ${evidenceBadgeClasses(batRel?.evidenceTier || bowlRel?.evidenceTier)}`}>
                      {humanizeEnum(batRel?.evidenceTier || bowlRel?.evidenceTier || 'NO_EXPOSURE')}
                    </span>
                    <span className="font-semibold text-rr-pink">View Profile →</span>
                  </div>
                </Link>
              );
            })}
          </div>
          <Pagination meta={playersQ.meta} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}

