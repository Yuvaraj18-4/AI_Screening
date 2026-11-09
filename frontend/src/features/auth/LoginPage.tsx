import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin, useCurrentUser } from "../../api/auth";
import { Button } from "../../components/Button";
import { Lock, Mail, AlertCircle } from "lucide-react";

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState("");

  const navigate = useNavigate();
  const loginMutation = useLogin();
  const { data: user } = useCurrentUser();

  // Redirect if already authenticated
  React.useEffect(() => {
    if (user) {
      if (user.role === "recruiter") navigate("/requisitions", { replace: true });
      else if (user.role === "client") navigate("/portal", { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!email || !password) {
      setFormError("Please fill in both email and password");
      return;
    }

    try {
      const loggedInUser = await loginMutation.mutateAsync({ email, password });
      if (loggedInUser.role === "recruiter") {
        navigate("/requisitions");
      } else {
        navigate("/portal");
      }
    } catch (err: any) {
      setFormError(err.message || "Failed to log in. Please check your credentials.");
    }
  };

  const fillDemo = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setFormError("");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 text-white font-black text-xl mb-4 shadow-sm">
          S
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">
          Sign in to ShortList
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          AI resume-screening and client shortlist portal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm rounded-xl border border-gray-200 sm:px-10">
          {formError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                Email address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="recruiter@example.com"
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md shadow-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md shadow-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full mt-2"
              isLoading={loginMutation.isPending}
            >
              Sign in
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs font-medium text-gray-500 mb-2 text-center">
              Quick Demo Logins:
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillDemo("recruiter@example.com", "recruiter123")}
              >
                Recruiter
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillDemo("client1@example.com", "client123")}
              >
                Client User
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
