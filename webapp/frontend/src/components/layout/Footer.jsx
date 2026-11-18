import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="mt-16 border-t border-rr-lavender/15 bg-rr-surface-deep/90 text-xs text-rr-lavender">
      <div className="mx-auto grid max-w-[1440px] gap-8 px-4 py-10 sm:px-6 md:grid-cols-4 lg:px-8">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-gradient-to-br from-rr-pink to-rr-gold font-mono text-[10px] font-extrabold text-rr-plum">
              RE
            </span>
            <span className="text-sm font-extrabold tracking-[0.08em] text-rr-light">
              RoyalsEdge
            </span>
          </div>
          <p className="mt-2 max-w-md leading-relaxed text-rr-lavender">
            <strong className="text-rr-light">IPL 2027 Performance &amp; Auction Intelligence Platform.</strong>{' '}
            Beyond the Numbers. Inside the Pressure. Evaluating T20 player reliability under match
            pressure across IPL and T20I seasons (2022–2026).
          </p>
          <p className="mt-3 text-[11px] text-rr-lavender/75">
            Independent research project built for SupeRR Selector Season 2. Not affiliated with or
            officially endorsed by Rajasthan Royals or the IPL.
          </p>
        </div>

        <div>
          <h4 className="font-semibold uppercase tracking-wider text-rr-light">Analytics</h4>
          <ul className="mt-2.5 space-y-1.5">
            <li><Link to="/overview" className="hover:text-rr-pink">Overview Dashboard</Link></li>
            <li><Link to="/pressure" className="hover:text-rr-pink">Pressure Intelligence</Link></li>
            <li><Link to="/batting" className="hover:text-rr-pink">Batting Rankings</Link></li>
            <li><Link to="/bowling" className="hover:text-rr-pink">Bowling Rankings</Link></li>
            <li><Link to="/players" className="hover:text-rr-pink">Player Explorer</Link></li>
            <li><Link to="/compare" className="hover:text-rr-pink">Compare Players</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold uppercase tracking-wider text-rr-light">Research & Scope</h4>
          <ul className="mt-2.5 space-y-1.5">
            <li><Link to="/matches" className="hover:text-rr-pink">Match Explorer</Link></li>
            <li><Link to="/methodology" className="hover:text-rr-pink">Methodology (20 Sections)</Link></li>
            <li><Link to="/reports" className="hover:text-rr-pink">Reports & Downloads</Link></li>
            <li><Link to="/admin" className="hover:text-rr-gold">Admin Console</Link></li>
          </ul>
          <div className="mt-4 rounded-lg border border-rr-lavender/15 bg-rr-plum/60 p-2.5 text-[11px]">
            <div>Coverage: <strong className="text-rr-light">IPL & T20I (2022–2026)</strong></div>
            <div>Data: <strong className="text-rr-light">193,988 Verified Deliveries</strong></div>
          </div>
        </div>
      </div>

      <div className="border-t border-rr-lavender/10 py-4 text-center text-[11px] text-rr-lavender/75">
        © {new Date().getFullYear()} RoyalsEdge · IPL 2027 Performance &amp; Auction Intelligence Platform · Zero Live or Fabricated Metrics
      </div>
    </footer>
  );
}

