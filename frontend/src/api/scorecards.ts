import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface Criterion {
  id?: number;
  name: string;
  kind: "experience" | "notice" | "location" | "skill" | "domain";
  must_have: boolean;
  weight: number;
  params: Record<string, any>;
  description: string;
}

export interface Scorecard {
  id: number;
  requisition_id: number;
  version: number;
  is_active: boolean;
  criteria: Criterion[];
  created_at: string;
}

export function useScorecard(requisitionId: number) {
  return useQuery<Scorecard | null>({
    queryKey: ["scorecard", requisitionId],
    queryFn: async () => {
      try {
        return await apiClient<Scorecard>(`/requisitions/${requisitionId}/scorecard`);
      } catch (err: any) {
        if (err.status === 404) return null;
        throw err;
      }
    },
    enabled: !!requisitionId,
  });
}

export function useSaveScorecard(requisitionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (criteria: Criterion[]) =>
      apiClient<Scorecard>(`/requisitions/${requisitionId}/scorecard`, {
        method: "PUT",
        body: JSON.stringify({ criteria }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scorecard", requisitionId] });
      queryClient.invalidateQueries({ queryKey: ["requisitions", requisitionId] });
    },
  });
}
