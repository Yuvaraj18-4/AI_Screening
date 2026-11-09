import { apiClient } from "./client";
import type { CriterionResultDetail } from "./candidates";

export interface PortalRequisition {
  id: number;
  title: string;
  department: string | null;
  location: string | null;
  status: string;
  submission_count: number;
}

export interface PortalSubmissionItem {
  submission_id: number;
  application_id: number;
  candidate_id: number;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string;
  stage: string;
  client_decision: string;
  submitted_at: string;
  weighted_score: number | null;
  must_have_gaps: string[];
  confidence_score: string | null;
  notes: string | null;
}

export interface PortalSubmissionDetail {
  submission_id: number;
  application_id: number;
  candidate_id: number;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string;
  stage: string;
  client_decision: string;
  submitted_at: string;
  weighted_score: number | null;
  must_have_gaps: string[];
  confidence_score: string | null;
  notes: string | null;
  proposed_slot: string | null;
  reject_reason: string | null;
  masked: boolean;
  criteria_results: CriterionResultDetail[];
}

export interface PortalDecisionPayload {
  decision: "shortlisted" | "rejected" | "propose_slot";
  reject_reason?: string | null;
  proposed_slot?: string | null;
  notes?: string | null;
}

export async function fetchPortalRequisitions(): Promise<PortalRequisition[]> {
  return apiClient<PortalRequisition[]>("/portal/requisitions");
}

export async function fetchPortalSubmissions(requisitionId: number): Promise<PortalSubmissionItem[]> {
  return apiClient<PortalSubmissionItem[]>(`/portal/requisitions/${requisitionId}/submissions`);
}

export async function fetchPortalSubmissionDetail(submissionId: number): Promise<PortalSubmissionDetail> {
  return apiClient<PortalSubmissionDetail>(`/portal/submissions/${submissionId}`);
}

export async function submitPortalDecision(
  submissionId: number,
  payload: PortalDecisionPayload,
): Promise<PortalSubmissionDetail> {
  return apiClient<PortalSubmissionDetail>(`/portal/submissions/${submissionId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
