import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface CriterionResultDetail {
  id: number;
  criterion_id: number;
  criterion_name: string;
  kind: string;
  must_have: boolean;
  weight: number;
  verdict: "met" | "partial" | "not_found" | "unclear" | "unverified";
  value: number;
  quote?: string | null;
  quote_verified: boolean;
  confidence: number;
  source: string;
}

export interface ScoreDetail {
  id: number;
  scorecard_version: number;
  total: number;
  confidence: "high" | "medium" | "low";
  status: "scored" | "ai_failed" | "pending";
  scoring_mode: string;
  must_have_gaps: string[];
  results: CriterionResultDetail[];
}

export interface ApplicationListItem {
  id: number;
  candidate_id: number;
  requisition_id: number;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string;
  current_role: string;
  location: string;
  experience_years: number;
  notice_days: number;
  stage: string;
  parse_quality: number;
  duplicate_of_id?: number | null;
  has_viewed: boolean;
  score?: ScoreDetail | null;
  created_at: string;
}

export interface ApplicationDetail {
  id: number;
  candidate_id: number;
  requisition_id: number;
  requisition_title: string;
  client_name: string;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string;
  current_role: string;
  location: string;
  skills: string[];
  employment: Array<{
    title: string;
    company: string;
    start?: string;
    end?: string;
  }>;
  experience_years: number;
  notice_days: number;
  current_ctc: string;
  expected_ctc: string;
  education: Array<{
    degree?: string;
    institution?: string;
    year?: string;
  }>;
  parse_quality: number;
  duplicate_of_id?: number | null;
  stage: string;
  cv_text: string;
  masked_text: string;
  has_viewed: boolean;
  score?: ScoreDetail | null;
  created_at: string;
}

export async function fetchApplications(
  requisitionId: number,
  options?: { sort?: string; stage?: string },
): Promise<ApplicationListItem[]> {
  const params = new URLSearchParams();
  if (options?.sort) params.set("sort", options.sort);
  if (options?.stage) params.set("stage", options.stage);
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiClient<ApplicationListItem[]>(`/requisitions/${requisitionId}/applications${q}`);
}

export async function updateApplicationStage(
  applicationId: number,
  stage: string,
  note?: string,
): Promise<ApplicationDetail> {
  return apiClient<ApplicationDetail>(`/applications/${applicationId}/stage`, {
    method: "POST",
    body: JSON.stringify({ stage, note }),
  });
}

export function useApplications(
  requisitionId: number,
  sort: string = "score",
  stage?: string,
) {
  return useQuery<ApplicationListItem[]>({
    queryKey: ["applications", requisitionId, sort, stage],
    queryFn: () => {
      const params = new URLSearchParams();
      if (sort) params.set("sort", sort);
      if (stage && stage !== "all") params.set("stage", stage);
      return apiClient<ApplicationListItem[]>(
        `/requisitions/${requisitionId}/applications?${params.toString()}`,
      );
    },
    enabled: !!requisitionId,
  });
}

export function useApplicationDetail(applicationId: number | null) {
  return useQuery<ApplicationDetail>({
    queryKey: ["application", applicationId],
    queryFn: () => apiClient<ApplicationDetail>(`/applications/${applicationId}`),
    enabled: !!applicationId,
  });
}

export function useSubmitApplication(requisitionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: number) =>
      apiClient(`/applications/${applicationId}/submit`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", requisitionId] });
      queryClient.invalidateQueries({ queryKey: ["application"] });
    },
  });
}

export function useRescoreApplication(requisitionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: number) =>
      apiClient(`/applications/${applicationId}/rescore`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", requisitionId] });
      queryClient.invalidateQueries({ queryKey: ["application"] });
    },
  });
}

export function useUpdateApplicationStage(requisitionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      applicationId,
      stage,
      note,
    }: {
      applicationId: number;
      stage: string;
      note?: string;
    }) =>
      apiClient(`/applications/${applicationId}/stage`, {
        method: "POST",
        body: JSON.stringify({ stage, note }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", requisitionId] });
      queryClient.invalidateQueries({ queryKey: ["application"] });
    },
  });
}

export function useResolveDuplicate(requisitionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      candidateId,
      action,
    }: {
      candidateId: number;
      action: "merge" | "keep";
    }) =>
      apiClient(`/candidates/${candidateId}/duplicate-resolution`, {
        method: "POST",
        body: JSON.stringify({ action }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", requisitionId] });
    },
  });
}
