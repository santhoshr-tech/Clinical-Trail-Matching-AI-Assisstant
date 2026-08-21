import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { BASE_URL } from './utils/apiClient';
import { DisclaimerBanner } from './components/Banner';
import { Navbar } from './components/Navbar';
import { PatientNavbar } from './components/PatientNavbar';
import { Footer } from './components/Footer';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ProtectedRoute } from './components/ProtectedRoute';

import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { PatientListPage } from './pages/PatientListPage';
import { PatientDetailsPage } from './pages/PatientDetailsPage';
import { PatientTimelinePage } from './pages/PatientTimelinePage';
import { DocumentUploadPage } from './pages/DocumentUploadPage';
import { DocumentExtractionReviewPage } from './pages/DocumentExtractionReviewPage';
import { TrialSearchPage } from './pages/TrialSearchPage';
import { TrialDetailsPage } from './pages/TrialDetailsPage';
import { TrialVersionHistoryPage } from './pages/TrialVersionHistoryPage';
import { CriteriaExtractionReviewPage } from './pages/CriteriaExtractionReviewPage';
import { ScreeningResultPage } from './pages/ScreeningResultPage';
import { EvidenceVerificationPage } from './pages/EvidenceVerificationPage';
import { ConflictResolverPage } from './pages/ConflictResolverPage';
import { WhatIfSimulatorPage } from './pages/WhatIfSimulatorPage';
import { EligibilityTimelinePage } from './pages/EligibilityTimelinePage';
import { CriteriaChangeImpactPage } from './pages/CriteriaChangeImpactPage';
import { RescreeningQueuePage } from './pages/RescreeningQueuePage';
import { CoordinatorReviewQueuePage } from './pages/CoordinatorReviewQueuePage';
import { InvestigatorReviewPage } from './pages/InvestigatorReviewPage';
import { DisagreementAnalyticsPage } from './pages/DisagreementAnalyticsPage';
import { ResearcherFeedbackPage } from './pages/ResearcherFeedbackPage';
import { EvaluationMetricsPage } from './pages/EvaluationMetricsPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { SettingsPage } from './pages/SettingsPage';

// Patient Portal Pages
import { PatientPrescriptionPage } from './pages/PatientPrescriptionPage';
import { PatientMedicinePage } from './pages/PatientMedicinePage';
import { PatientFoodPage } from './pages/PatientFoodPage';
import { FloatingWidgets } from './components/FloatingWidgets';
import { TrialSiteMap } from './components/TrialSiteMap';
import { ChatbotModal } from './components/ChatbotModal';

const AppContent: React.FC = () => {
  const { user } = useAuth();
  const [currentLanguage, setCurrentLanguage] = useState<string>('English');
  const [standaloneChatOpen, setStandaloneChatOpen] = useState<boolean>(true);

  // Load language preference on login
  useEffect(() => {
    if (user?.role === 'patient') {
      fetch(`${BASE_URL}/api/v1/patient-portal/preferences`, {
        headers: {
          'X-User-Email': user.email,
          'X-User-Role': user.role,
        },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success && data.data?.preferredLanguage) {
            setCurrentLanguage(data.data.preferredLanguage);
          }
        })
        .catch((e) => console.error(e));
    }
  }, [user]);

  const isPatient = user?.role === 'patient';

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
      {isPatient ? (
        <PatientNavbar
          currentLanguage={currentLanguage}
          onLanguageChange={(lang) => setCurrentLanguage(lang)}
        />
      ) : (
        <Navbar />
      )}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Patient Portal Routes */}
          <Route
            path="/patient-portal/prescription"
            element={
              <ProtectedRoute allowedRoles={['patient', 'admin']}>
                <PatientPrescriptionPage currentLanguage={currentLanguage} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/medicines"
            element={
              <ProtectedRoute allowedRoles={['patient', 'admin']}>
                <PatientMedicinePage currentLanguage={currentLanguage} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/food"
            element={
              <ProtectedRoute allowedRoles={['patient', 'admin']}>
                <PatientFoodPage currentLanguage={currentLanguage} />
              </ProtectedRoute>
            }
          />

          {/* Protected Workspace Coordinator Routes */}
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/patients" element={<ProtectedRoute><PatientListPage /></ProtectedRoute>} />
          <Route path="/patients/:id" element={<ProtectedRoute><PatientDetailsPage /></ProtectedRoute>} />
          <Route path="/patients/:id/timeline" element={<ProtectedRoute><PatientTimelinePage /></ProtectedRoute>} />

          <Route path="/documents/upload" element={<ProtectedRoute><DocumentUploadPage /></ProtectedRoute>} />
          <Route path="/documents/:id/review" element={<ProtectedRoute><DocumentExtractionReviewPage /></ProtectedRoute>} />

          <Route path="/trials/search" element={<ProtectedRoute><TrialSearchPage /></ProtectedRoute>} />
          <Route path="/trials/map" element={<ProtectedRoute><TrialSiteMap /></ProtectedRoute>} />
          <Route path="/trials/:id" element={<ProtectedRoute><TrialDetailsPage /></ProtectedRoute>} />
          <Route path="/trials/:id/versions" element={<ProtectedRoute><TrialVersionHistoryPage /></ProtectedRoute>} />
          <Route path="/trials/:id/criteria-review" element={<ProtectedRoute><CriteriaExtractionReviewPage /></ProtectedRoute>} />
          <Route path="/research-assistant" element={<ProtectedRoute><ChatbotModal isOpen={standaloneChatOpen} onClose={() => setStandaloneChatOpen(false)} /></ProtectedRoute>} />

          <Route path="/screening/:id" element={<ProtectedRoute><ScreeningResultPage /></ProtectedRoute>} />
          <Route path="/evidence/:id" element={<ProtectedRoute><EvidenceVerificationPage /></ProtectedRoute>} />
          <Route path="/conflicts" element={<ProtectedRoute><ConflictResolverPage /></ProtectedRoute>} />
          <Route path="/what-if" element={<ProtectedRoute><WhatIfSimulatorPage /></ProtectedRoute>} />
          <Route path="/eligibility-timeline" element={<ProtectedRoute><EligibilityTimelinePage /></ProtectedRoute>} />
          <Route path="/criteria-impact" element={<ProtectedRoute><CriteriaChangeImpactPage /></ProtectedRoute>} />
          <Route path="/rescreening-queue" element={<ProtectedRoute><RescreeningQueuePage /></ProtectedRoute>} />

          <Route path="/coordinator-queue" element={<ProtectedRoute allowedRoles={['admin', 'research_coordinator', 'investigator']}><CoordinatorReviewQueuePage /></ProtectedRoute>} />
          <Route path="/investigator-review" element={<ProtectedRoute allowedRoles={['admin', 'investigator']}><InvestigatorReviewPage /></ProtectedRoute>} />
          <Route path="/disagreement-analytics" element={<ProtectedRoute><DisagreementAnalyticsPage /></ProtectedRoute>} />
          <Route path="/feedback" element={<ProtectedRoute><ResearcherFeedbackPage /></ProtectedRoute>} />

          <Route path="/evaluation-metrics" element={<ProtectedRoute><EvaluationMetricsPage /></ProtectedRoute>} />
          <Route path="/notifications" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
          <Route path="/audit-logs" element={<ProtectedRoute allowedRoles={['admin', 'research_coordinator', 'investigator', 'reviewer']}><AuditLogsPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

          {/* Fallback route */}
          <Route path="*" element={<Navigate to={isPatient ? '/patient-portal/prescription' : '/'} replace />} />
        </Routes>
      </main>
      <Footer />
      {/* Phase 8 Floating Round Widgets: Lower Right Location Tracker + Upper Lower Right RAG Chatbot */}
      <FloatingWidgets />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
};
