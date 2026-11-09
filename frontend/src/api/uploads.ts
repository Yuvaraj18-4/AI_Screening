import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface BatchFileProgress {
  id: number;
  filename: string;
  size: number;
  candidate_id: number;
  candidate_name: string;
  parse_status: "ok" | "needs_review" | "failed";
  parse_error?: string | null;
  is_duplicate: boolean;
}

export interface BatchProgress {
  batch_id: number;
  total: number;
  queued: number;
  running: number;
  done: number;
  failed: number;
  files: BatchFileProgress[];
}

export function useBatchProgress(batchId: number | null) {
  return useQuery<BatchProgress>({
    queryKey: ["uploads", "progress", batchId],
    queryFn: () => apiClient<BatchProgress>(`/uploads/${batchId}/progress`),
    enabled: !!batchId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      // Stop polling once all files are either done or failed
      if (data.done + data.failed >= data.total && data.total > 0) {
        return false;
      }
      return 2000;
    },
  });
}

export function useUploadCVs(requisitionId: number) {
  return useMutation({
    mutationFn: async (files: File[]) => {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }
      return apiClient<{ batch_id: number; total: number; message: string }>(
        `/requisitions/${requisitionId}/uploads`,
        {
          method: "POST",
          body: formData,
        },
      );
    },
  });
}
