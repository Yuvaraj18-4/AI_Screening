import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface Requisition {
  id: number;
  client_id: number;
  title: string;
  jd_text: string;
  status: "draft" | "active" | "closed";
  owner_id: number;
  client_name?: string;
  applications_count: number;
  active_scorecard_version?: number | null;
  created_at: string;
}

export function useRequisitions() {
  return useQuery<Requisition[]>({
    queryKey: ["requisitions"],
    queryFn: () => apiClient<Requisition[]>("/requisitions"),
  });
}

export function useRequisition(id: number) {
  return useQuery<Requisition>({
    queryKey: ["requisitions", id],
    queryFn: () => apiClient<Requisition>(`/requisitions/${id}`),
    enabled: !!id,
  });
}

export function useCreateRequisition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { client_id: number; title: string; jd_text: string }) =>
      apiClient<Requisition>("/requisitions", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requisitions"] });
    },
  });
}

export function useUpdateRequisition(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { title?: string; jd_text?: string; status?: string }) =>
      apiClient<Requisition>(`/requisitions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requisitions"] });
      queryClient.invalidateQueries({ queryKey: ["requisitions", id] });
    },
  });
}

export function useExtractJD(id: number) {
  return useMutation({
    mutationFn: () =>
      apiClient<{ title: string; criteria: any[] }>(`/requisitions/${id}/jd/extract`, {
        method: "POST",
      }),
  });
}
