import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface User {
  id: number;
  email: string;
  name: string;
  role: "recruiter" | "client";
  client_id?: number | null;
  created_at: string;
}

export interface HealthInfo {
  status: string;
  database: string;
  scoring_mode: "llm" | "heuristic";
  worker_status: string;
}

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: () => apiClient<User>("/auth/me"),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useHealth() {
  return useQuery<HealthInfo>({
    queryKey: ["health"],
    queryFn: () => apiClient<HealthInfo>("/health"),
    refetchInterval: 30000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      apiClient<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["auth", "me"], data);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient<{ ok: boolean }>("/auth/logout", {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.clear();
      window.location.href = "/login";
    },
  });
}
