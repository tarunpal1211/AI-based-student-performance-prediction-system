import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";

import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import PredictPage from "./pages/PredictPage";
import SimulatorPage from "./pages/SimulatorPage";
import ProgressPage from "./pages/ProgressPage";
import HistoryPage from "./pages/HistoryPage";
import AtRiskPage from "./pages/AtRiskPage";
import AnalyticsPage from "./pages/AnalyticsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2, // 2 min
      retry: 1,
    },
  },
});

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<Layout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="predict" element={<PredictPage />} />
                <Route path="simulator" element={<SimulatorPage />} />
                <Route path="progress" element={<ProgressPage />} />
                <Route path="history" element={<HistoryPage />} />
                <Route path="at-risk" element={<AtRiskPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
              </Route>
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;
