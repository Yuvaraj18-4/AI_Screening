import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { RequireRole } from "./RequireRole";
import { LoginPage } from "../features/auth/LoginPage";
import { RequisitionListPage } from "../features/requisitions/RequisitionListPage";
import { RequisitionDetailPage } from "../features/requisitions/RequisitionDetailPage";
import { PortalRequisitionsPage } from "../features/portal/PortalRequisitionsPage";
import { PortalSubmissionDetailPage } from "../features/portal/PortalSubmissionDetailPage";
import { Navbar } from "../components/Navbar";
import { HeuristicBanner } from "../components/HeuristicBanner";

const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <HeuristicBanner />
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
};

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Authenticated routes sharing standard layout */}
        <Route element={<AppLayout />}>
          {/* Recruiter routes */}
          <Route
            path="/requisitions"
            element={
              <RequireRole role="recruiter">
                <RequisitionListPage />
              </RequireRole>
            }
          />
          <Route
            path="/requisitions/:id"
            element={
              <RequireRole role="recruiter">
                <RequisitionDetailPage />
              </RequireRole>
            }
          />

          {/* Client portal routes */}
          <Route
            path="/portal"
            element={
              <RequireRole role="client">
                <PortalRequisitionsPage />
              </RequireRole>
            }
          />
          <Route
            path="/portal/submissions/:id"
            element={
              <RequireRole role="client">
                <PortalSubmissionDetailPage />
              </RequireRole>
            }
          />
        </Route>

        {/* Default route */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* 404 */}
        <Route
          path="*"
          element={
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
              <div className="text-center">
                <h1 className="text-6xl font-black text-gray-300">404</h1>
                <p className="mt-2 text-sm text-gray-600 font-medium">Page not found</p>
                <a
                  href="/"
                  className="mt-4 inline-block px-4 py-2 text-xs font-semibold text-blue-600 hover:underline"
                >
                  Return to Home
                </a>
              </div>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
