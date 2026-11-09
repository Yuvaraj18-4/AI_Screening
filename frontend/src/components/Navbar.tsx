import React from "react";
import { LogOut, Briefcase, Layers } from "lucide-react";
import { useCurrentUser, useLogout } from "../api/auth";
import { Badge } from "./Badge";
import { Link } from "react-router-dom";

export const Navbar: React.FC = () => {
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 font-bold text-gray-900 text-base tracking-tight">
            <span className="flex items-center justify-center w-7 h-7 rounded bg-blue-600 text-white font-black text-sm">
              S
            </span>
            <span>ShortList</span>
          </Link>
          {user?.role === "recruiter" && (
            <nav className="hidden sm:flex items-center gap-4 text-sm font-medium text-gray-600">
              <Link
                to="/requisitions"
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md hover:text-gray-900 hover:bg-gray-100 transition-colors"
              >
                <Briefcase className="w-4 h-4" />
                <span>Requisitions</span>
              </Link>
            </nav>
          )}
          {user?.role === "client" && (
            <nav className="flex items-center gap-4 text-sm font-medium text-gray-600">
              <Link
                to="/portal"
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md hover:text-gray-900 hover:bg-gray-100 transition-colors"
              >
                <Layers className="w-4 h-4" />
                <span>Review Portal</span>
              </Link>
            </nav>
          )}
        </div>

        {user && (
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-semibold text-gray-900">{user.name}</span>
              <span className="text-[10px] text-gray-500">{user.email}</span>
            </div>
            <Badge variant={user.role === "recruiter" ? "info" : "success"} size="sm">
              {user.role}
            </Badge>
            <button
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
              className="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
