import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext.jsx';
import { WorkspaceProvider } from './contexts/WorkspaceContext.jsx';
import MainLayout from './layouts/MainLayout.jsx';
import LoginPage from './pages/LoginPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import PatientRecordsPage from './pages/PatientRecordsPage.jsx';
import PatientDetailPage from './pages/PatientDetailPage.jsx';
import RiskAssessmentPage from './pages/RiskAssessmentPage.jsx';
import LabResultsPage from './pages/LabResultsPage.jsx';
import ResistanceClassificationPage from './pages/ResistanceClassificationPage.jsx';
import DiscussionPage from './pages/DiscussionPage.jsx';
import NotificationsPage from './pages/NotificationsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Opening your workspace…</div>;
  if (!user) return <LoginPage />;
  return <WorkspaceProvider><Routes><Route element={<MainLayout />}>
    <Route path="/" element={<Navigate to="/dashboard" replace />} />
    <Route path="/login" element={<Navigate to="/dashboard" replace />} />
    <Route path="/dashboard" element={<DashboardPage />} />
    <Route path="/patients" element={<PatientRecordsPage />} />
    <Route path="/patients/:patientId" element={<PatientDetailPage />} />
    <Route path="/risk-assessment" element={<RiskAssessmentPage />} />
    <Route path="/lab-results" element={<LabResultsPage />} />
    <Route path="/resistance-classification" element={<ResistanceClassificationPage />} />
    <Route path="/discussion" element={<DiscussionPage />} />
    <Route path="/notifications" element={<NotificationsPage />} />
    <Route path="/settings" element={<SettingsPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route></Routes></WorkspaceProvider>;
}
