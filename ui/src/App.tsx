import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './api/client'
import { Layout } from './components/layout/Layout'
import { ErrorBoundary } from './components/shared/ErrorBoundary'
import { ToastProvider } from './components/shared/Toast'
import { LoginPage } from './pages/Login'
import { DashboardPage } from './pages/Dashboard'
import { ServersPage } from './pages/Servers'
import { CapabilitiesPage } from './pages/Capabilities'
import { AgentClassesPage } from './pages/AgentClasses'
import { PoliciesPage } from './pages/Policies'
import { AuditPage } from './pages/Audit'
import { ApprovalsPage } from './pages/Approvals'
import { PacksPage } from './pages/Packs'
import { AlertsPage } from './pages/Alerts'
import { AdminUsersPage } from './pages/AdminUsers'
import { TrustPosturePage } from './pages/TrustPosture'
import { ReviewsPage } from './pages/Reviews'  // Schema-digest review page for approving/rejecting stale mappings

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ErrorBoundary>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<Layout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/servers" element={<ServersPage />} />
                <Route path="/capabilities" element={<CapabilitiesPage />} />
                <Route path="/agent-classes" element={<AgentClassesPage />} />
                <Route path="/policies" element={<PoliciesPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/approvals" element={<ApprovalsPage />} />
                <Route path="/packs" element={<PacksPage />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="/admin/users" element={<AdminUsersPage />} />
                <Route path="/trust" element={<TrustPosturePage />} />
                <Route path="/reviews" element={<ReviewsPage />} /> {/* Schema-digest review workflow */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  )
}
