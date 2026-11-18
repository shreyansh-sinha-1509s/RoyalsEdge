import { ChevronDown, Download } from 'lucide-react';
import { useState } from 'react';
import { ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtNum } from '../utils/formatters.js';

export function MethodologyPage() {
  const methQ = useApiQuery((signal) => api.getMethodology(signal), []);
  const [openSec, setOpenSec] = useState(1);

  if (methQ.loading) return <LoadingState label="Loading 20-section methodology report..." />;
  if (methQ.error) return <ErrorState error={methQ.error} onRetry={methQ.refetch} />;
  if (!methQ.data) return null;

  const { sections, rankingMethodComparison, robustnessTests, shortlistAlternatives } = methQ.data;
  const narrowMisses = shortlistAlternatives.filter((r) => r.audit_group === 'narrow_miss_ranks_11_to_15');

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Transparent Research Documentation · 20 Verified Sections"
        title="Methodology, Robustness & Limitations"
        subtitle="Complete reproducible pipeline from raw competition CSVs through Model C pre-delivery pressure, Empirical Bayes shrinkage, volume-free reliability, and Balanced Primary rankings."
        actions={
          <a
            href={api.getReportDownloadUrl('methodology-report-pdf')}
            className="inline-flex items-center gap-2 rounded-lg bg-rr-pink px-4 py-2 text-xs font-bold text-white shadow-rr-pink hover:bg-rr-pink/90"
          >
            <Download className="h-3.5 w-3.5" />
            Download Methodology PDF
          </a>
        }
      />

      {/* Ranking Philosophy Comparison */}
      {rankingMethodComparison?.length > 0 && (
        <section className="rr-card overflow-hidden">
          <div className="border-b border-rr-lavender/15 px-5 py-3.5">
            <h2 className="text-base font-bold text-rr-light">Ranking Philosophy Comparison</h2>
            <p className="text-xs text-rr-lavender">
              Balanced Primary (50/25/15/10) selected over Performance-Dominant (65/20/10/5) and Reliability-Dominant (30/50/10/10).
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase tracking-wider text-rr-lavender">
                <tr>
                  <th className="px-4 py-2.5">Discipline</th>
                  <th className="px-4 py-2.5">Approach</th>
                  <th className="px-4 py-2.5">Weights (Perf/Rel/Ext/Evid)</th>
                  <th className="px-4 py-2.5 text-right">Spearman vs Primary</th>
                  <th className="px-4 py-2.5 text-right">Top-10 Overlap</th>
                  <th className="px-4 py-2.5 text-right">Top-10 Mean Rel</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {rankingMethodComparison.map((r, i) => {
                  const isSel = String(r.is_selected_primary).toLowerCase() === 'true';
                  return (
                    <tr key={i} className={isSel ? 'bg-rr-pink/10 font-semibold' : ''}>
                      <td className="px-4 py-2.5 capitalize">{r.discipline}</td>
                      <td className="px-4 py-2.5">
                        {r.approach}
                        {isSel && <span className="ml-2 rounded bg-rr-pink px-1.5 py-0.5 text-[10px] text-white">SELECTED</span>}
                      </td>
                      <td className="px-4 py-2.5 font-mono">{r.weights_perf_rel_ext_evid}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{fmtNum(r.spearman_vs_primary, 4)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{r.top10_overlap_with_primary_count}/10 ({r.top10_overlap_with_primary_pct}%)</td>
                      <td className="px-4 py-2.5 text-right font-mono text-rr-gold">{fmtNum(r.top10_mean_reliability, 1)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 20 Interactive Methodology Sections */}
      <section className="space-y-2.5">
        <h2 className="text-base font-bold text-rr-light">Complete 20-Section Technical Specification</h2>
        {sections.map((sec) => {
          const isOpen = openSec === sec.sectionNumber;
          return (
            <div key={sec.sectionNumber} id={sec.slug} className="rr-card overflow-hidden">
              <button
                type="button"
                onClick={() => setOpenSec(isOpen ? null : sec.sectionNumber)}
                className="flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left transition hover:bg-rr-plum/40"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-rr-plum font-mono text-xs font-bold text-rr-pink">
                    {String(sec.sectionNumber).padStart(2, '0')}
                  </span>
                  <span className="text-sm font-semibold text-rr-light">{sec.title}</span>
                </div>
                <ChevronDown className={`h-4 w-4 shrink-0 text-rr-lavender transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>
              {isOpen && (
                <div className="border-t border-rr-lavender/15 bg-rr-plum/40 px-5 py-4 text-xs leading-relaxed text-rr-light/90">
                  {sec.formulasJson?.length > 0 && (
                    <div className="mb-3 rounded-lg border border-rr-gold/30 bg-rr-plum p-3 font-mono text-[11px] text-rr-gold">
                      {sec.formulasJson.map((f, idx) => (
                        <div key={idx}>{f}</div>
                      ))}
                    </div>
                  )}
                  <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-rr-light/90">
                    {sec.contentMd}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </section>

      {/* Robustness Tests & Narrow Misses */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rr-card overflow-hidden">
          <div className="border-b border-rr-lavender/15 px-5 py-3.5">
            <h2 className="text-sm font-bold text-rr-light">Robustness Across 7 Alternative Models</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase text-rr-lavender">
                <tr>
                  <th className="px-3.5 py-2.5">Disc</th>
                  <th className="px-3.5 py-2.5">Specification</th>
                  <th className="px-3.5 py-2.5 text-right">Spearman</th>
                  <th className="px-3.5 py-2.5 text-right">Top-10</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10 font-mono">
                {robustnessTests.map((r, i) => (
                  <tr key={i}>
                    <td className="px-3.5 py-2 font-sans capitalize">{r.discipline}</td>
                    <td className="px-3.5 py-2 font-sans text-rr-lavender">{r.robustness_test}</td>
                    <td className="px-3.5 py-2 text-right">{fmtNum(r.spearman_corr_vs_primary, 4)}</td>
                    <td className="px-3.5 py-2 text-right text-rr-teal">{r.top10_overlap_count}/10 ({r.top10_overlap_pct}%)</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rr-card overflow-hidden">
          <div className="border-b border-rr-lavender/15 px-5 py-3.5">
            <h2 className="text-sm font-bold text-rr-light">Documented Narrow Misses (Ranks #11–#15)</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-rr-plum/80 text-[11px] uppercase text-rr-lavender">
                <tr>
                  <th className="px-3.5 py-2.5">Disc / Rk</th>
                  <th className="px-3.5 py-2.5">Player</th>
                  <th className="px-3.5 py-2.5 text-right">Score</th>
                  <th className="px-3.5 py-2.5 text-right">Rel</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rr-lavender/10">
                {narrowMisses.map((r, i) => (
                  <tr key={i}>
                    <td className="px-3.5 py-2 font-mono text-rr-gold">
                      {r.discipline === 'batting' ? 'Bat' : 'Bowl'} #{Math.trunc(Number(r.primary_rank))}
                    </td>
                    <td className="px-3.5 py-2 font-semibold text-rr-light">
                      {r.player_name} <span className="font-mono text-[10px] text-rr-lavender">ID {r.player_id}</span>
                    </td>
                    <td className="px-3.5 py-2 text-right font-mono">{fmtNum(r.final_ranking_score, 2)}</td>
                    <td className="px-3.5 py-2 text-right font-mono text-rr-lavender">{fmtNum(r.reliability_score, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

