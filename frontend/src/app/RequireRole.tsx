import React from "react";
import { Navigate } from "react-router-dom";
import { useCurrentUser } from "../api/auth";
import { Loader2 } from "lucide-react";

interface RequireRoleProps {
  role: "recruiter" | "client";
  children: React.ReactNode;
}

export function RequireRole({ role, children }: RequireRoleProps) {
  const { data: user, isLoading, isError } = useCurrentUser();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (isError || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== role) {
    return (
      <Navigate
        to={user.role === "recruiter" ? "/requisitions" : "/portal"}
        replace
      />
    );
  }

  return <>{children}</>;
}
