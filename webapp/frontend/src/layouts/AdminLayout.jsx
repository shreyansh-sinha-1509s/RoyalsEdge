import { Activity, CheckCircle2, Database, FileText, LogOut, Shield } from 'lucide-react';
import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { RoyalsEdgeLogo } from '../components/common/RoyalsEdgeLogo.jsx';
import { LoadingState } from '../components/common/States.jsx';
import { useAdminAuth } from '../hooks/useAdminAuth.jsx';

const ADMIN_LINKS = [
  { to: '/admin', end: true, label: 'Dashboard & Health', icon: Activity },
  { to: '/admin/imports', label: 'Data Imports', icon: Database },
  { to: '/admin/reconciliation', label: 'Top-10 Reconciliation', icon: CheckCircle2 },
  { to: '/admin/audit', label: 'Audit & System Logs', icon: FileText },
];

export function AdminLayout() {
  const { admin, checking, logout } = useAdminAuth();
  const location = useLocation();

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-rr-plum p-6">
        <div className="w-full max-w-md">
          <LoadingState label="Verifying administrator session..." />
        </div>
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }

  return (
    <div className="min-h-screen bg-rr-plum text-rr-light">
      <header className="sticky top-0 z-30 border-b border-rr-lavender/15 bg-rr-surface-deep/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <Link to="/" className="group flex items-center" aria-label="RoyalsEdge Home">
              <span className="sr-only">RoyalsEdge</span>
              <RoyalsEdgeLogo variant="horizontal" size={30} interactive />
            </Link>
            <span className="inline-flex items-center gap-1 rounded-full border border-rr-gold/35 bg-rr-gold/10 px-2.5 py-0.5 text-[11px] font-semibold text-rr-gold">
              <Shield className="h-3 w-3" />
              ADMIN CONSOLE
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <span className="hidden text-rr-lavender sm:inline">{admin.email}</span>
            <Link
              to="/overview"
              className="rounded-lg border border-rr-lavender/25 px-3 py-1.5 text-rr-lavender hover:border-rr-pink hover:text-rr-light"
            >
              Public App
            </Link>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-1.5 rounded-lg bg-rr-coral/15 px-3 py-1.5 font-semibold text-rr-coral transition hover:bg-rr-coral/25"
            >
              <LogOut className="h-3.5 w-3.5" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[240px_1fr] lg:px-8">
        <aside className="space-y-1">
          {ADMIN_LINKS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-sm font-medium transition ${
                    isActive
                      ? 'bg-rr-pink/15 text-rr-pink border border-rr-pink/35'
                      : 'text-rr-lavender hover:bg-rr-surface hover:text-rr-light'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
          <div className="mt-4 rounded-xl border border-rr-lavender/15 bg-rr-surface/60 p-3.5 text-[11px] text-rr-lavender">
            <div className="font-semibold text-rr-gold">Governance Guardrail</div>
            <p className="mt-1 leading-relaxed">
              Manual ranking editing is disabled by architecture. All analytical records update exclusively
              via validated CSV re-imports reconciled against official Phase 6 outputs.
            </p>
          </div>
        </aside>

        <main className="min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

