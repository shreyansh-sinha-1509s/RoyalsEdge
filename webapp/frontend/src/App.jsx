import { Navigate, Route, Routes } from 'react-router-dom';
import { AdminAuthProvider } from './hooks/useAdminAuth.jsx';
import { AdminLayout } from './layouts/AdminLayout.jsx';
import { MainLayout } from './layouts/MainLayout.jsx';
import { BattingPage } from './pages/BattingPage.jsx';
import { BowlingPage } from './pages/BowlingPage.jsx';
import { ComparePage } from './pages/ComparePage.jsx';
import { HomePage } from './pages/HomePage.jsx';
import { MatchDetailPage } from './pages/MatchDetailPage.jsx';
import { MatchesPage } from './pages/MatchesPage.jsx';
import { MethodologyPage } from './pages/MethodologyPage.jsx';
import { OverviewPage } from './pages/OverviewPage.jsx';
import { PlayerProfilePage } from './pages/PlayerProfilePage.jsx';
import { PlayersPage } from './pages/PlayersPage.jsx';
import { PressurePage } from './pages/PressurePage.jsx';
import { ReportsPage } from './pages/ReportsPage.jsx';
import { AdminAuditPage } from './pages/admin/AdminAuditPage.jsx';
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage.jsx';
import { AdminImportsPage } from './pages/admin/AdminImportsPage.jsx';
import { AdminLoginPage } from './pages/admin/AdminLoginPage.jsx';
import { AdminReconciliationPage } from './pages/admin/AdminReconciliationPage.jsx';

export function AppRoutes() {
  return (
    <AdminAuthProvider>
      <Routes>
        {/* Cinematic Homepage (full-bleed night stadium layout) */}
        <Route path="/" element={<HomePage />} />

        {/* Clean Professional Analytics Shell */}
        <Route element={<MainLayout />}>
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/batting" element={<BattingPage />} />
          <Route path="/bowling" element={<BowlingPage />} />
          <Route path="/pressure" element={<PressurePage />} />
          <Route path="/players" element={<PlayersPage />} />
          <Route path="/players/:playerId" element={<PlayerProfilePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/matches" element={<MatchesPage />} />
          <Route path="/matches/:matchId" element={<MatchDetailPage />} />
          <Route path="/methodology" element={<MethodologyPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Route>

        {/* Protected Admin Console */}
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboardPage />} />
          <Route path="imports" element={<AdminImportsPage />} />
          <Route path="reconciliation" element={<AdminReconciliationPage />} />
          <Route path="audit" element={<AdminAuditPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AdminAuthProvider>
  );
}

export default AppRoutes;

