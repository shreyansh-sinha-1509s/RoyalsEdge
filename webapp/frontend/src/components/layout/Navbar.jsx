import { ChevronDown, Menu, Moon, Search, Shield, Sun, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '../../hooks/useTheme.js';
import { api } from '../../services/api.js';
import { RoyalsEdgeLogo, RoyalsEdgeWordmark } from '../common/RoyalsEdgeLogo.jsx';

const NAV_GROUPS = [
  {
    label: 'Analytics',
    items: [
      { to: '/overview', label: 'Overview Dashboard', desc: 'Project KPIs & Top 10 snapshot' },
      { to: '/pressure', label: 'Pressure Intelligence', desc: 'Chase, First-Innings & Bowling Model C' },
      { to: '/batting', label: 'Batting Rankings', desc: 'Top 10 & 173 eligible batters' },
      { to: '/bowling', label: 'Bowling Rankings', desc: 'Top 10 & 165 eligible bowlers' },
      { to: '/matches', label: 'Match Explorer', desc: '853 historical IPL & T20I matches' },
    ],
  },
  {
    label: 'Players',
    items: [
      { to: '/players', label: 'Player Explorer', desc: 'Search all 1,217 players by ID or name' },
      { to: '/compare', label: 'Compare Players', desc: 'Side-by-side same-discipline analysis' },
    ],
  },
  {
    label: 'Research',
    items: [
      { to: '/methodology', label: 'Methodology', desc: '20 transparent research sections' },
      { to: '/reports', label: 'Reports & Downloads', desc: 'Official CSV, Excel & PDF exports' },
    ],
  },
];

export function Navbar({ transparent = false }) {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [openGroup, setOpenGroup] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const navRef = useRef(null);

  useEffect(() => {
    setOpenGroup(null);
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onDocClick = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setOpenGroup(null);
      }
    };
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen((v) => !v);
      } else if (e.key === 'Escape') {
        setSearchOpen(false);
        setOpenGroup(null);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    window.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  useEffect(() => {
    if (!searchOpen || query.trim().length < 2) {
      setResults([]);
      return undefined;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await api.getPlayers({ search: query.trim(), limit: 8 }, controller.signal);
        setResults(res.data || []);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 220);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, searchOpen]);

  const shellClass = transparent
    ? 'fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-rr-plum/65 backdrop-blur-md'
    : 'sticky top-0 z-40 border-b border-rr-lavender/15 bg-rr-plum/95 backdrop-blur-md';

  return (
    <>
      <header ref={navRef} className={shellClass}>
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="group flex items-center gap-2.5 focus:outline-none" aria-label="RoyalsEdge Home">
            <RoyalsEdgeLogo
              variant="icon"
              theme={transparent ? 'dark' : 'auto'}
              size={38}
              interactive
            />
            <div className="flex flex-col justify-center">
              <span className="sr-only">RoyalsEdge</span>
              <RoyalsEdgeWordmark
                height={18}
                theme={transparent ? 'dark' : 'auto'}
              />
              <span className="mt-0.5 hidden text-[9px] font-semibold tracking-[0.14em] text-rr-gold sm:block">
                BEYOND THE NUMBERS. INSIDE THE PRESSURE.
              </span>
            </div>
          </Link>

          {/* Desktop Grouped Navigation */}
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary Navigation">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  isActive ? 'bg-rr-pink/15 text-rr-pink' : 'text-rr-light/90 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              Home
            </NavLink>

            <NavLink
              to="/overview"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  isActive ? 'bg-rr-pink/15 text-rr-pink' : 'text-rr-light/90 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              Overview
            </NavLink>

            {NAV_GROUPS.map((group) => {
              const isGroupActive = group.items.some((item) => location.pathname.startsWith(item.to));
              const isOpen = openGroup === group.label;
              return (
                <div key={group.label} className="relative">
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => setOpenGroup(isOpen ? null : group.label)}
                    className={`inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                      isGroupActive || isOpen
                        ? 'bg-rr-pink/15 text-rr-pink'
                        : 'text-rr-light/90 hover:bg-white/5 hover:text-white'
                    }`}
                  >
                    {group.label}
                    <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isOpen && (
                    <div className="absolute left-0 mt-2 w-72 rounded-xl border border-rr-lavender/20 bg-rr-surface p-2 shadow-rr">
                      {group.items.map((item) => (
                        <NavLink
                          key={item.to}
                          to={item.to}
                          className={({ isActive }) =>
                            `block rounded-lg px-3 py-2.5 transition ${
                              isActive
                                ? 'bg-rr-pink/15 text-rr-pink'
                                : 'text-rr-light hover:bg-rr-plum/60'
                            }`
                          }
                        >
                          <div className="text-xs font-semibold">{item.label}</div>
                          <div className="mt-0.5 text-[11px] text-rr-lavender">{item.desc}</div>
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </nav>

          {/* Right Utilities */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              aria-label="Search players"
              className="inline-flex items-center gap-2 rounded-lg border border-rr-lavender/25 bg-rr-surface/70 px-3 py-1.5 text-xs text-rr-lavender transition hover:border-rr-pink hover:text-rr-light"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Search players</span>
              <kbd className="hidden rounded bg-rr-plum px-1.5 py-0.5 font-mono text-[10px] text-rr-lavender md:inline">
                Ctrl K
              </kbd>
            </button>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle color theme"
              className="rounded-lg border border-rr-lavender/25 p-2 text-rr-lavender transition hover:border-rr-gold hover:text-rr-gold"
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>

            <Link
              to="/admin"
              aria-label="Admin Console"
              className="hidden items-center gap-1.5 rounded-lg border border-rr-lavender/25 px-2.5 py-1.5 text-xs font-medium text-rr-lavender transition hover:border-rr-pink hover:text-rr-pink sm:inline-flex"
            >
              <Shield className="h-3.5 w-3.5" />
              Admin
            </Link>

            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle mobile menu"
              className="rounded-lg border border-rr-lavender/25 p-2 text-rr-light lg:hidden"
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Mobile Drawer */}
        {mobileOpen && (
          <div className="border-t border-rr-lavender/15 bg-rr-plum px-4 py-4 lg:hidden">
            <div className="space-y-4">
              <div className="flex flex-col gap-1">
                <NavLink to="/" end className="rounded-lg px-3 py-2 text-sm font-semibold text-rr-light hover:bg-rr-surface">
                  Home
                </NavLink>
                <NavLink to="/overview" className="rounded-lg px-3 py-2 text-sm font-semibold text-rr-light hover:bg-rr-surface">
                  Overview Dashboard
                </NavLink>
              </div>
              {NAV_GROUPS.map((group) => (
                <div key={group.label}>
                  <div className="px-3 text-[11px] font-bold uppercase tracking-wider text-rr-pink">
                    {group.label}
                  </div>
                  <div className="mt-1 flex flex-col gap-0.5">
                    {group.items.map((item) => (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        className={({ isActive }) =>
                          `rounded-lg px-3 py-2 text-sm ${
                            isActive ? 'bg-rr-pink/15 font-semibold text-rr-pink' : 'text-rr-light/90 hover:bg-rr-surface'
                          }`
                        }
                      >
                        {item.label}
                      </NavLink>
                    ))}
                  </div>
                </div>
              ))}
              <div className="border-t border-rr-lavender/15 pt-3">
                <Link to="/admin" className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-rr-gold">
                  <Shield className="h-4 w-4" />
                  Admin Console
                </Link>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Global Player Search Modal */}
      {searchOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 pt-20 backdrop-blur-sm"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-rr-lavender/25 bg-rr-surface p-4 shadow-rr"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 border-b border-rr-lavender/20 pb-3">
              <Search className="h-4 w-4 text-rr-pink" />
              <input
                autoFocus
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search player by name, team, or integer player_id (e.g., 4722)..."
                className="w-full bg-transparent text-sm text-rr-light placeholder:text-rr-lavender/70 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setSearchOpen(false)}
                className="rounded p-1 text-rr-lavender hover:text-rr-light"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-3 max-h-80 overflow-y-auto">
              {searching && <p className="py-4 text-center text-xs text-rr-lavender">Searching players...</p>}
              {!searching && query.trim().length < 2 && (
                <p className="py-4 text-center text-xs text-rr-lavender">
                  Type at least 2 characters or a player ID. Shared names are disambiguated by unique player_id.
                </p>
              )}
              {!searching && query.trim().length >= 2 && results.length === 0 && (
                <p className="py-4 text-center text-xs text-rr-lavender">No matching players found.</p>
              )}
              <ul className="divide-y divide-rr-lavender/10">
                {results.map((p) => (
                  <li key={p.playerId}>
                    <button
                      type="button"
                      onClick={() => {
                        setSearchOpen(false);
                        setQuery('');
                        navigate(`/players/${p.playerId}`);
                      }}
                      className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition hover:bg-rr-plum/60"
                    >
                      <div>
                        <div className="flex items-center gap-2 text-sm font-semibold text-rr-light">
                          {p.displayName}
                          <span className="rounded bg-rr-plum px-1.5 py-0.5 font-mono text-[10px] text-rr-gold">
                            ID {p.playerId}
                          </span>
                          {p.sharesNameWithOtherId && (
                            <span className="rounded bg-rr-pink/20 px-1.5 py-0.5 text-[10px] text-rr-pink">
                              Shared Name
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-rr-lavender">
                          {p.inferredPlayingRole || 'Player'} · {p.teamNames || 'No team metadata'}
                        </div>
                      </div>
                      <div className="text-right font-mono text-[11px] text-rr-lavender">
                        {p.battingRanking?.rank && <div className="text-rr-pink">Bat #{p.battingRanking.rank}</div>}
                        {p.bowlingRanking?.rank && <div className="text-rr-teal">Bowl #{p.bowlingRanking.rank}</div>}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

