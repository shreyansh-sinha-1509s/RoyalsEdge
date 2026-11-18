import { motion } from 'framer-motion';
import {
  ArrowRight,
  ChevronDown,
  Flame,
  Gauge,
  Layers,
  ShieldCheck,
  Target,
  Trophy,
} from 'lucide-react';
import { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorState, LoadingState } from '../components/common/States.jsx';
import { StadiumHeroFallback } from '../components/hero/StadiumHeroFallback.jsx';
import { Footer } from '../components/layout/Footer.jsx';
import { Navbar } from '../components/layout/Navbar.jsx';
import { useApiQuery } from '../hooks/useApiQuery.js';
import { api } from '../services/api.js';
import { fmtInt, fmtNum } from '../utils/formatters.js';

const StadiumScene3D = lazy(() => import('../components/hero/StadiumScene3D.jsx'));

function detect3DCapability() {
  if (typeof window === 'undefined') return false;
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return false;
  if (window.innerWidth < 768) return false;
  if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) return false;
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

export function HomePage() {
  const heroRef = useRef(null);
  const [canRender3D, setCanRender3D] = useState(false);
  const [heroVisible, setHeroVisible] = useState(true);
  const [activeTierIdx, setActiveTierIdx] = useState(3);

  const { data: overview, loading, error, refetch } = useApiQuery(
    (signal) => api.getOverview(signal),
    []
  );

  useEffect(() => {
    setCanRender3D(detect3DCapability());
    if (!heroRef.current || typeof IntersectionObserver === 'undefined') return undefined;
    const obs = new IntersectionObserver(
      ([entry]) => setHeroVisible(entry.isIntersecting),
      { threshold: 0.05 }
    );
    obs.observe(heroRef.current);
    return () => obs.disconnect();
  }, []);

  const snap = overview?.snapshot;
  const tiers = [
    { name: 'LOW PRESSURE', pct: 25, desc: 'Comfortable chase / steady early platform', color: 'bg-rr-teal' },
    { name: 'MODERATE PRESSURE', pct: 50, desc: 'Balanced match tension near format par', color: 'bg-rr-blue' },
    { name: 'HIGH PRESSURE', pct: 75, desc: 'Top ~30% match difficulty: RRR squeeze or wicket cluster', color: 'bg-rr-gold' },
    { name: 'EXTREME PRESSURE', pct: 100, desc: 'Top ~10% crunch deliveries where matches are won or lost', color: 'bg-rr-pink' },
  ];

  return (
    <div className="min-h-screen bg-rr-plum text-rr-light">
      <Navbar transparent />

      {/* FULL-SCREEN CINEMATIC NIGHT STADIUM HERO */}
      <section
        ref={heroRef}
        className="relative flex min-h-screen flex-col justify-between overflow-hidden pt-20"
      >
        <StadiumHeroFallback />
        {canRender3D && (
          <Suspense fallback={null}>
            <StadiumScene3D active={heroVisible} />
          </Suspense>
        )}

        {/* Balanced radial vignette scrim for crisp WCAG AA readability over 3D floodlights */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 74% 66% at 50% 45%, rgba(20,10,28,0.76) 0%, rgba(20,10,28,0.48) 58%, rgba(16,7,23,0.84) 100%)',
          }}
        />

        <div className="relative z-10 mx-auto flex w-full max-w-[1440px] flex-1 flex-col items-center justify-center px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, ease: 'easeOut' }}
            className="mx-auto flex w-full max-w-4xl flex-col items-center text-center"
          >
            {/* 1. Centered Top Pill Badge */}
            <div className="mb-5 inline-flex max-w-full flex-wrap items-center justify-center gap-2 rounded-full border border-rr-gold/40 bg-rr-plum/75 px-4 py-1.5 text-center text-[10px] font-semibold uppercase tracking-[0.14em] text-rr-gold shadow-[0_0_24px_rgba(216,180,90,0.12)] backdrop-blur-md sm:text-[11px] sm:tracking-[0.18em]">
              <Flame className="h-3.5 w-3.5 shrink-0 text-rr-pink" />
              <span>IPL 2027 Performance &amp; Auction Intelligence Platform</span>
            </div>

            {/* 2. Centered Main Heading */}
            <h1 className="text-5xl font-extrabold tracking-tight text-white drop-shadow-[0_6px_28px_rgba(0,0,0,0.65)] sm:text-6xl lg:text-7xl">
              RoyalsEdge
            </h1>

            {/* 3. Centered Brand Tagline */}
            <p className="mt-4 font-mono text-xs font-semibold uppercase tracking-[0.2em] text-rr-pink sm:text-sm sm:tracking-[0.24em] md:text-base">
              BEYOND THE NUMBERS. INSIDE THE PRESSURE.
            </p>

            {/* 4. Centered Description Paragraph */}
            <p className="mt-5 max-w-[740px] text-sm leading-relaxed text-rr-light/90 sm:text-base md:text-lg">
              Discover how the world&apos;s T20 players perform when every run, wicket, and delivery
              matters. Built on pre-delivery pressure modeling, Empirical Bayes shrinkage, and
              volume-free reliability analysis.
            </p>

            {/* 5. Centered Horizontal CTA Button Row */}
            <div className="mt-8 flex w-full flex-col items-center justify-center gap-3.5 sm:w-auto sm:flex-row sm:flex-wrap">
              <Link
                to="/overview"
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-rr-pink px-7 py-3.5 text-sm font-bold tracking-wide text-white shadow-rr-pink transition hover:bg-rr-pink/90 sm:w-auto"
              >
                ENTER ANALYTICS
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/batting"
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-rr-gold/55 bg-rr-plum/75 px-7 py-3.5 text-sm font-bold tracking-wide text-rr-gold backdrop-blur-md transition hover:bg-rr-gold hover:text-rr-plum sm:w-auto"
              >
                <Trophy className="h-4 w-4" />
                VIEW TOP 10 PLAYERS
              </Link>
            </div>

            {/* 6. Centered Dataset Statistics Row */}
            <div className="mt-10 grid w-full max-w-xl grid-cols-1 gap-4 border-t border-white/15 pt-6 min-[420px]:grid-cols-3 min-[420px]:gap-4 sm:max-w-2xl sm:gap-8">
              <div className="flex flex-col items-center">
                <div className="font-mono text-xl font-bold text-white tabular-nums sm:text-2xl">
                  {snap ? fmtInt(snap.deliveries) : '—'}
                </div>
                <div className="mt-0.5 text-[11px] uppercase tracking-wider text-rr-lavender">
                  Deliveries
                </div>
              </div>
              <div className="flex flex-col items-center">
                <div className="font-mono text-xl font-bold text-white tabular-nums sm:text-2xl">
                  {snap ? fmtInt(snap.matchesWithBallData) : '—'}
                </div>
                <div className="mt-0.5 text-[11px] uppercase tracking-wider text-rr-lavender">
                  Matches
                </div>
              </div>
              <div className="flex flex-col items-center">
                <div className="font-mono text-xl font-bold text-rr-gold tabular-nums sm:text-2xl">
                  {snap ? snap.seasonsCoverage : '2022–2026'}
                </div>
                <div className="mt-0.5 text-[11px] uppercase tracking-wider text-rr-lavender">
                  IPL + T20I
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Scroll Indicator */}
        <div className="relative z-10 flex justify-center pb-6">
          <a
            href="#snapshot"
            className="inline-flex flex-col items-center gap-1 text-[11px] uppercase tracking-widest text-rr-lavender transition hover:text-rr-gold"
          >
            <span>Explore Intelligence</span>
            <ChevronDown className="h-4 w-4 animate-bounce" />
          </a>
        </div>
      </section>

      {/* ANALYTICAL SECTIONS BELOW THE STADIUM FOLD */}
      <div id="snapshot" className="mx-auto max-w-[1440px] space-y-16 px-4 py-16 sm:px-6 lg:px-8">
        {/* Section 1: Verified Project Snapshot */}
        <section>
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-[0.16em] text-rr-pink">
                Section 01 · Verified Historical Scope
              </span>
              <h2 className="mt-1 text-2xl font-bold text-rr-light sm:text-3xl">Project Snapshot</h2>
            </div>
            <Link to="/overview" className="inline-flex items-center gap-1 text-xs font-semibold text-rr-gold hover:underline">
              Open Full Overview Dashboard <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {loading && <LoadingState label="Loading verified dataset metrics from API..." />}
          {error && <ErrorState error={error} onRetry={refetch} />}
          {snap && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {[
                { label: 'Regular Deliveries', value: fmtInt(snap.deliveries), sub: 'Verified IPL + T20I' },
                { label: 'Matches Analyzed', value: fmtInt(snap.matchesWithBallData), sub: `${fmtInt(snap.totalEligibleMatches)} eligible total` },
                { label: 'Reconciled Innings', value: fmtInt(snap.innings), sub: '0 reconciliation diffs' },
                { label: 'Batters Analyzed', value: fmtInt(snap.battersAnalyzed), sub: `${fmtInt(snap.eligibleBatters)} primary eligible` },
                { label: 'Bowlers Analyzed', value: fmtInt(snap.bowlersAnalyzed), sub: `${fmtInt(snap.eligibleBowlers)} primary eligible` },
                { label: 'Season Coverage', value: snap.seasonsCoverage, sub: 'Model C Primary' },
              ].map((item) => (
                <div key={item.label} className="rr-card border-t-2 border-t-rr-pink/70 p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-rr-lavender">
                    {item.label}
                  </div>
                  <div className="mt-2 font-mono text-2xl font-bold text-rr-light tabular-nums">
                    {item.value}
                  </div>
                  <div className="mt-1 text-[11px] text-rr-lavender/80">{item.sub}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Section 2: The Pressure Intelligence Engine */}
        <section className="rr-card p-6 sm:p-8">
          <div className="grid gap-8 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="text-xs font-bold uppercase tracking-[0.16em] text-rr-pink">
                Section 02 · Pre-Delivery Context Only
              </span>
              <h2 className="mt-1 text-2xl font-bold text-rr-light sm:text-3xl">
                The Pressure Intelligence Engine
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-rr-lavender">
                Pressure measures <strong className="text-rr-light">match difficulty before the ball is bowled</strong> — never
                using the current delivery&apos;s runs, wicket, or match outcome. Model C computes separate
                Leave-One-Match-Out (LOMO) IPL and T20I par trajectories across three distinct frameworks:
              </p>

              <div className="mt-5 space-y-3">
                {[
                  { title: 'Chase Pressure (Innings 2)', desc: 'Required run rate demand, wicket scarcity, acceleration gap, endgame urgency & RRR×Wickets interaction.' },
                  { title: 'First-Innings Batting Pressure (Innings 1)', desc: 'Score deficit vs format par, wicket collapse severity, CRR lag & late-innings urgency.' },
                  { title: 'Bowling Pressure (Innings 1 & 2)', desc: 'Opposite wicket polarity: close chase / opposition surge with wickets in hand, phase hazard & striker threat.' },
                ].map((m) => (
                  <div key={m.title} className="rounded-lg border border-rr-lavender/15 bg-rr-plum/60 p-3.5">
                    <div className="text-sm font-semibold text-rr-gold">{m.title}</div>
                    <p className="mt-1 text-xs text-rr-lavender">{m.desc}</p>
                  </div>
                ))}
              </div>

              <Link
                to="/pressure"
                className="mt-5 inline-flex items-center gap-2 rounded-lg bg-rr-pink/15 px-4 py-2.5 text-xs font-bold text-rr-pink transition hover:bg-rr-pink hover:text-white"
              >
                Explore Pressure Intelligence <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {/* Interactive LOW -> EXTREME Pressure Meter */}
            <div className="rounded-xl border border-rr-lavender/20 bg-rr-plum/75 p-5">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-rr-lavender">Model C Intensity Escalation</span>
                <span className="font-mono text-rr-gold">0–100 Scale</span>
              </div>

              <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-rr-surface">
                <div
                  className={`h-full transition-all duration-500 ${tiers[activeTierIdx].color}`}
                  style={{ width: `${tiers[activeTierIdx].pct}%` }}
                />
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {tiers.map((tier, idx) => (
                  <button
                    key={tier.name}
                    type="button"
                    onClick={() => setActiveTierIdx(idx)}
                    className={`rounded-lg border px-2.5 py-2 text-left text-[11px] font-semibold transition ${
                      activeTierIdx === idx
                        ? 'border-rr-pink bg-rr-pink/15 text-white'
                        : 'border-rr-lavender/15 bg-rr-surface/50 text-rr-lavender hover:border-rr-lavender/40'
                    }`}
                  >
                    {tier.name.replace(' PRESSURE', '')}
                  </button>
                ))}
              </div>

              <div className="mt-4 rounded-lg border border-rr-lavender/15 bg-rr-surface/70 p-4">
                <div className="font-mono text-xs font-bold text-rr-gold">{tiers[activeTierIdx].name}</div>
                <p className="mt-1 text-xs text-rr-light/90">{tiers[activeTierIdx].desc}</p>
                <p className="mt-2 text-[11px] text-rr-lavender">
                  Non-circular validation: aggregate batting SR drops monotonically{' '}
                  <span className="font-mono text-rr-light">145.3 → 139.9 → 136.6 → 128.1</span> and bowling
                  economy climbs <span className="font-mono text-rr-light">8.07 → 8.61 → 9.12 → 10.95</span>.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Top Performers Spotlight (Real Phase 6 Records) */}
        {overview && (
          <section>
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-[0.16em] text-rr-pink">
                  Section 03 · Official Phase 6 Shortlist
                </span>
                <h2 className="mt-1 text-2xl font-bold text-rr-light sm:text-3xl">
                  Top Performers Under Pressure
                </h2>
              </div>
              <div className="flex gap-3 text-xs font-semibold">
                <Link to="/batting" className="text-rr-pink hover:underline">Full Top 10 Batters →</Link>
                <Link to="/bowling" className="text-rr-teal hover:underline">Full Top 10 Bowlers →</Link>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              {[
                { title: 'Top 5 Batters (Balanced Primary)', items: overview.top10Batters.slice(0, 5), accent: 'text-rr-pink', discipline: 'Batting' },
                { title: 'Top 5 Bowlers (Balanced Primary)', items: overview.top10Bowlers.slice(0, 5), accent: 'text-rr-teal', discipline: 'Bowling' },
              ].map((group) => (
                <div key={group.title} className="rr-card p-5">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className={`text-sm font-bold uppercase tracking-wider ${group.accent}`}>{group.title}</h3>
                    <span className="font-mono text-[11px] text-rr-lavender">Click player for profile</span>
                  </div>
                  <div className="space-y-2.5">
                    {group.items.map((p) => (
                      <Link
                        key={`${group.discipline}-${p.playerId}`}
                        to={`/players/${p.playerId}`}
                        className="flex items-center justify-between gap-3 rounded-lg border border-rr-lavender/15 bg-rr-plum/60 px-3.5 py-2.5 transition hover:border-rr-pink"
                      >
                        <div className="flex items-center gap-3">
                          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-rr-surface font-mono text-xs font-bold text-rr-gold">
                            #{p.rank}
                          </span>
                          <div>
                            <div className="text-sm font-semibold text-rr-light">
                              {p.playerName}{' '}
                              <span className="font-mono text-[10px] text-rr-lavender">ID {p.playerId}</span>
                            </div>
                            <div className="text-[11px] text-rr-lavender">
                              {p.role} · {p.competitionContext}
                            </div>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-3 text-right font-mono text-xs tabular-nums">
                          <div>
                            <div className="text-[10px] text-rr-lavender">Score</div>
                            <div className="font-bold text-rr-light">{fmtNum(p.finalRankingScore, 1)}</div>
                          </div>
                          <div>
                            <div className="text-[10px] text-rr-lavender">Rel</div>
                            <div className="text-rr-gold">{fmtNum(p.reliabilityScore, 1)}</div>
                          </div>
                          <div>
                            <div className="text-[10px] text-rr-lavender">Evid</div>
                            <div className="text-rr-teal">{fmtNum(p.evidenceScore, 1)}</div>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Section 4: Three Separate Pillars */}
        <section>
          <span className="text-xs font-bold uppercase tracking-[0.16em] text-rr-pink">
            Section 04 · Conceptual Rigor
          </span>
          <h2 className="mt-1 text-2xl font-bold text-rr-light sm:text-3xl">
            Why Reliability Matters Alongside Performance
          </h2>
          <div className="mt-6 grid gap-5 md:grid-cols-3">
            {[
              {
                icon: Target,
                title: '1. Performance Effectiveness (50%)',
                color: 'text-rr-pink',
                body: 'Format- and phase-adjusted RVAE / RSAE plus wicket value, shrunk via Empirical Bayes (k = 8.65 matches batting, k = 30.00 matches bowling) so hot 2-match streaks never hijack rankings.',
              },
              {
                icon: Gauge,
                title: '2. Volume-Free Reliability (25%)',
                color: 'text-rr-gold',
                body: 'Consistency across innings, conditions, and seasons on variance-stabilized spell residuals. Near-zero correlation with ball volume (+0.100 bat / +0.165 bowl). Missing reliability stays NULL.',
              },
              {
                icon: ShieldCheck,
                title: '3. Evidence & Uncertainty (10% + CIs)',
                color: 'text-rr-teal',
                body: 'Whole-match clustered bootstrap 95% confidence intervals and 1,000 Monte Carlo rank simulations explicitly communicate where ranks are certain vs. closely matched.',
              },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.title} className="rr-card p-5">
                  <Icon className={`h-6 w-6 ${card.color}`} />
                  <h3 className="mt-3 text-base font-bold text-rr-light">{card.title}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-rr-lavender">{card.body}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 5: 6-Stage Research Pipeline */}
        <section className="rr-card p-6 sm:p-8">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-[0.16em] text-rr-pink">
                Section 05 · Transparent Research Workflow
              </span>
              <h2 className="mt-1 text-2xl font-bold text-rr-light">From Raw Deliveries to Final Rankings</h2>
            </div>
            <Link to="/methodology" className="inline-flex items-center gap-1 text-xs font-semibold text-rr-gold hover:underline">
              Read Complete 20-Section Methodology <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            {(overview?.pipelineStages || [
              { step: 1, title: 'Raw Data', detail: '200,999 raw deliveries' },
              { step: 2, title: 'Data Cleaning', detail: '193,988 eligible deliveries' },
              { step: 3, title: 'Pressure Modeling', detail: 'Model C LOMO 0–100' },
              { step: 4, title: 'Player Performance', detail: 'RVAE / RSAE + EB' },
              { step: 5, title: 'Reliability', detail: 'Volume-free consistency' },
              { step: 6, title: 'Final Rankings', detail: 'Balanced Primary Top 10' },
            ]).map((st) => (
              <Link
                key={st.step}
                to="/methodology"
                className="group rounded-lg border border-rr-lavender/15 bg-rr-plum/60 p-4 transition hover:border-rr-pink"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-rr-pink">0{st.step}</span>
                  <Layers className="h-3.5 w-3.5 text-rr-lavender group-hover:text-rr-gold" />
                </div>
                <div className="mt-2 text-sm font-bold text-rr-light">{st.title}</div>
                <p className="mt-1 text-[11px] leading-snug text-rr-lavender">{st.detail}</p>
              </Link>
            ))}
          </div>
        </section>

        {/* Section 6: Final CTA */}
        <section className="rounded-2xl border border-rr-pink/35 bg-gradient-to-r from-rr-surface via-rr-plum to-rr-surface p-8 text-center shadow-rr">
          <h2 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            THE NUMBERS TELL A STORY. PRESSURE REVEALS THE PLAYER.
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-rr-lavender">
            Inspect verified Top 10 shortlists, compare player reliability profiles, or download the
            complete competition methodology package.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              to="/batting"
              className="rounded-lg bg-rr-pink px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-white transition hover:bg-rr-pink/90"
            >
              Explore Player Rankings
            </Link>
            <Link
              to="/methodology"
              className="rounded-lg border border-rr-gold/50 px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-rr-gold transition hover:bg-rr-gold hover:text-rr-plum"
            >
              Explore Methodology
            </Link>
            <Link
              to="/reports"
              className="rounded-lg border border-rr-lavender/35 px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-rr-light transition hover:border-rr-pink hover:text-rr-pink"
            >
              Download Official Reports
            </Link>
          </div>
        </section>
      </div>

      <Footer />
    </div>
  );
}

