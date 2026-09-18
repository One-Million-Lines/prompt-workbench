import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedLayout } from './components/ProtectedLayout';
import { LoginPage } from './pages/LoginPage';
import { RegistryPage } from './pages/registry/RegistryPage';
import { EvaluationsPage } from './pages/evaluations/EvaluationsPage';
import { DatasetsList } from './pages/evaluations/DatasetsList';
import { DatasetDetail } from './pages/evaluations/DatasetDetail';
import { RunsList } from './pages/evaluations/RunsList';
import { RunDetail } from './pages/evaluations/RunDetail';
import { NewRun } from './pages/evaluations/NewRun';
import { ObservabilityPage } from './pages/observability/ObservabilityPage';
import { AllCalls } from './pages/observability/AllCalls';
import { CaptureInbox } from './pages/observability/CaptureInbox';
import { SettingsPage } from './pages/settings/SettingsPage';

/**
 * Application route table. `/login` is public; everything else is nested under
 * the ProtectedLayout which enforces authentication and renders app chrome.
 */
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedLayout />}>
        <Route index element={<Navigate to="/registry" replace />} />

        {/* Prompt Registry (list + editor share one screen) */}
        <Route path="registry" element={<RegistryPage />} />
        <Route path="registry/:promptId" element={<RegistryPage />} />

        {/* Evaluations */}
        <Route path="evaluations" element={<EvaluationsPage />}>
          <Route index element={<Navigate to="datasets" replace />} />
          <Route path="datasets" element={<DatasetsList />} />
          <Route path="datasets/:id" element={<DatasetDetail />} />
          <Route path="runs" element={<RunsList />} />
          <Route path="runs/new" element={<NewRun />} />
          <Route path="runs/:id" element={<RunDetail />} />
        </Route>

        {/* Observability */}
        <Route path="observability" element={<ObservabilityPage />}>
          <Route index element={<Navigate to="calls" replace />} />
          <Route path="calls" element={<AllCalls />} />
          <Route path="captures" element={<CaptureInbox />} />
        </Route>

        {/* Settings */}
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/registry" replace />} />
    </Routes>
  );
}
