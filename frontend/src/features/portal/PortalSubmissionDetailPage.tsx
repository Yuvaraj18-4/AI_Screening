import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Calendar,
  Lock,
  Unlock,
  AlertTriangle,
  Mail,
  Phone,
  ShieldCheck,
  Clock,
  Sparkles,
} from "lucide-react";
import {
  fetchPortalSubmissionDetail,
  submitPortalDecision,
  type PortalSubmissionDetail,
} from "../../api/portal";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { EvidenceItem } from "../../components/EvidenceItem";
import { ScoreRing } from "../../components/ScoreRing";
import { Skeleton } from "../../components/Skeleton";

export const PortalSubmissionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const submissionId = Number(id);

  const [detail, setDetail] = useState<PortalSubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Decision Modal States
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectError, setRejectError] = useState<string | null>(null);

  const [slotModalOpen, setSlotModalOpen] = useState(false);
  const [proposedSlot, setProposedSlot] = useState("");
  const [slotNotes, setSlotNotes] = useState("");
  const [slotError, setSlotError] = useState<string | null>(null);

  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (submissionId) {
      loadDetail();
    }
  }, [submissionId]);

  const loadDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchPortalSubmissionDetail(submissionId);
      setDetail(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load candidate submission");
    } finally {
      setLoading(false);
    }
  };

  const handleShortlist = async () => {
    try {
      setActionLoading(true);
      const updated = await submitPortalDecision(submissionId, { decision: "shortlisted" });
      setDetail(updated);
    } catch (err: any) {
      alert(err?.message || "Failed to shortlist candidate");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectReason.trim()) {
      setRejectError("Rejection reason is required");
      return;
    }
    try {
      setActionLoading(true);
      setRejectError(null);
      const updated = await submitPortalDecision(submissionId, {
        decision: "rejected",
        reject_reason: rejectReason.trim(),
      });
      setDetail(updated);
      setRejectModalOpen(false);
    } catch (err: any) {
      setRejectError(err?.message || "Failed to reject candidate");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmSlot = async () => {
    if (!proposedSlot) {
      setSlotError("Interview slot date/time is required");
      return;
    }
    try {
      setActionLoading(true);
      setSlotError(null);
      const updated = await submitPortalDecision(submissionId, {
        decision: "propose_slot",
        proposed_slot: new Date(proposedSlot).toISOString(),
        notes: slotNotes.trim() || undefined,
      });
      setDetail(updated);
      setSlotModalOpen(false);
    } catch (err: any) {
      setSlotError(err?.message || "Failed to propose interview slot");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <ErrorState message={error || "Candidate not found"} onRetry={loadDetail} />
      </div>
    );
  }

  const isShortlisted = detail.stage === "client_shortlisted" || detail.stage === "interview";
  const isRejected = detail.stage === "rejected";

  return (
    <div className="min-h-screen bg-gray-50 pb-28">
      {/* Top Bar Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            to="/portal"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Shortlists</span>
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Stage:</span>
            <Badge
              variant={isShortlisted ? "success" : isRejected ? "danger" : "info"}
              size="sm"
            >
              {detail.stage.replace("_", " ")}
            </Badge>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Candidate Profile Header Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                {detail.weighted_score !== null ? (
                  <ScoreRing score={Math.round(detail.weighted_score)} size={64} />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center font-bold text-gray-400">
                    N/A
                  </div>
                )}
              </div>
              <div>
                <h1 className="text-2xl font-black text-gray-900 tracking-tight">
                  {detail.candidate_name}
                </h1>
                <p className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span>Submitted on {new Date(detail.submitted_at).toLocaleDateString()}</span>
                </p>

                {/* Must-have gap indicator */}
                {detail.must_have_gaps && detail.must_have_gaps.length > 0 && (
                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-amber-800 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                      Must-have gaps identified:
                    </span>
                    {detail.must_have_gaps.map((gap, i) => (
                      <Badge key={i} variant="warning" size="sm">
                        {gap}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Decision Status Pill */}
            <div className="flex md:flex-col items-end justify-between md:justify-center border-t md:border-t-0 pt-4 md:pt-0 border-gray-100">
              <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
                Client Decision
              </span>
              <div className="mt-1">
                {isShortlisted && (
                  <div className="flex items-center gap-1.5 text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg text-xs font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Shortlisted for Interview</span>
                  </div>
                )}
                {isRejected && (
                  <div className="flex items-center gap-1.5 text-rose-700 bg-rose-50 border border-rose-200 px-3 py-1.5 rounded-lg text-xs font-bold">
                    <XCircle className="w-4 h-4 text-rose-600" />
                    <span>Candidate Rejected</span>
                  </div>
                )}
                {!isShortlisted && !isRejected && (
                  <div className="flex items-center gap-1.5 text-blue-700 bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold">
                    <Clock className="w-4 h-4 text-blue-500" />
                    <span>Pending Your Decision</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Rejection / Slot Notification Banner */}
          {detail.reject_reason && (
            <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800">
              <span className="font-bold">Rejection reason:</span> {detail.reject_reason}
            </div>
          )}
          {detail.proposed_slot && (
            <div className="mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-xs text-indigo-900 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-600 flex-shrink-0" />
              <span>
                <span className="font-bold">Proposed interview slot:</span>{" "}
                {new Date(detail.proposed_slot).toLocaleString()}
              </span>
            </div>
          )}
        </div>

        {/* Privacy & Contact Info Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
            <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              {detail.masked ? (
                <>
                  <Lock className="w-4 h-4 text-amber-500" />
                  <span>Candidate Contact Info (Masked)</span>
                </>
              ) : (
                <>
                  <Unlock className="w-4 h-4 text-emerald-600" />
                  <span>Candidate Contact Info (Unmasked)</span>
                </>
              )}
            </h2>
            <span className="text-[11px] text-gray-500">
              {detail.masked
                ? "Revealed upon shortlist decision"
                : "Unlocked for interview scheduling"}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-xs text-gray-500 flex items-center gap-1 mb-1">
                <Mail className="w-3.5 h-3.5" />
                <span>Email Address</span>
              </span>
              <span
                className={`text-sm font-mono font-medium ${
                  detail.masked ? "text-amber-700 bg-amber-50 px-2 py-0.5 rounded" : "text-gray-900"
                }`}
              >
                {detail.candidate_email}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-xs text-gray-500 flex items-center gap-1 mb-1">
                <Phone className="w-3.5 h-3.5" />
                <span>Phone Number</span>
              </span>
              <span
                className={`text-sm font-mono font-medium ${
                  detail.masked ? "text-amber-700 bg-amber-50 px-2 py-0.5 rounded" : "text-gray-900"
                }`}
              >
                {detail.candidate_phone}
              </span>
            </div>
          </div>
        </div>

        {/* Evidence & Scorecard Breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-600" />
                <span>Verified Scorecard Evidence</span>
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Each criterion was evaluated against the candidate's verified resume text.
              </p>
            </div>
            <div className="text-xs text-gray-400">
              {detail.criteria_results.length} criteria evaluated
            </div>
          </div>

          {detail.criteria_results.length === 0 ? (
            <EmptyState
              title="No criteria results available"
              description="Scorecard evaluation data has not been recorded for this application."
              icon={<Sparkles className="w-8 h-8" />}
            />
          ) : (
            <div className="space-y-3">
              {detail.criteria_results.map((result) => (
                <EvidenceItem key={result.criterion_id} result={result} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sticky Bottom Action Bar (Mobile Responsive down to 375px) */}
      <div className="fixed bottom-0 inset-x-0 bg-white/95 backdrop-blur border-t border-gray-200 p-3 sm:p-4 z-40 shadow-lg">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs text-gray-600">
            <span className="font-semibold text-gray-900">{detail.candidate_name}</span>
            <span>•</span>
            <span>Score: {detail.weighted_score !== null ? `${Math.round(detail.weighted_score)}%` : "N/A"}</span>
          </div>

          <div className="w-full sm:w-auto flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRejectModalOpen(true)}
              disabled={actionLoading || isRejected}
              className="flex-1 sm:flex-initial text-rose-600 border-rose-200 hover:bg-rose-50"
            >
              <XCircle className="w-4 h-4 mr-1.5" />
              <span>Reject</span>
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setSlotModalOpen(true)}
              disabled={actionLoading || isRejected}
              className="flex-1 sm:flex-initial"
            >
              <Calendar className="w-4 h-4 mr-1.5" />
              <span>Propose Slot</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={handleShortlist}
              disabled={actionLoading || isShortlisted}
              className="flex-1 sm:flex-initial"
            >
              <CheckCircle2 className="w-4 h-4 mr-1.5" />
              <span>Shortlist</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Reject Reason Modal */}
      <Dialog
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Candidate"
      >
        <div className="space-y-4">
          <p className="text-xs text-gray-600">
            Please provide a specific rejection reason for the candidate. This helps maintain audit transparency.
          </p>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Rejection Reason <span className="text-rose-500">*</span>
            </label>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Notice period exceeds 60 days maximum client cutoff requirement"
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {rejectError && (
            <p className="text-xs text-rose-600 font-medium">{rejectError}</p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRejectModalOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleConfirmReject}
              disabled={actionLoading}
            >
              Confirm Rejection
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Propose Interview Slot Modal */}
      <Dialog
        isOpen={slotModalOpen}
        onClose={() => setSlotModalOpen(false)}
        title="Propose Interview Slot"
      >
        <div className="space-y-4">
          <p className="text-xs text-gray-600">
            Select a proposed date and time to schedule the client interview. The candidate stage will advance to Interview.
          </p>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Proposed Date & Time <span className="text-rose-500">*</span>
            </label>
            <input
              type="datetime-local"
              value={proposedSlot}
              onChange={(e) => setProposedSlot(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Interview Notes (Optional)
            </label>
            <textarea
              value={slotNotes}
              onChange={(e) => setSlotNotes(e.target.value)}
              placeholder="e.g. Focus on microservices architecture and Kafka integration experience"
              rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {slotError && (
            <p className="text-xs text-rose-600 font-medium">{slotError}</p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSlotModalOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleConfirmSlot}
              disabled={actionLoading}
            >
              Schedule Slot
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
