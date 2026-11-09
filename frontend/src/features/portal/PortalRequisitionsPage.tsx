import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Briefcase,
  ChevronRight,
  Clock,
  Sparkles,
  AlertTriangle,
  UserCheck,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  fetchPortalRequisitions,
  fetchPortalSubmissions,
  type PortalRequisition,
  type PortalSubmissionItem,
} from "../../api/portal";
import { Badge } from "../../components/Badge";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Skeleton } from "../../components/Skeleton";
import { ScoreRing } from "../../components/ScoreRing";

export const PortalRequisitionsPage: React.FC = () => {
  const [requisitions, setRequisitions] = useState<PortalRequisition[]>([]);
  const [selectedReqId, setSelectedReqId] = useState<number | null>(null);
  const [submissions, setSubmissions] = useState<PortalSubmissionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRequisitions();
  }, []);

  const loadRequisitions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchPortalRequisitions();
      setRequisitions(data);
      if (data.length > 0) {
        setSelectedReqId(data[0].id);
        loadSubmissions(data[0].id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load client requisitions");
    } finally {
      setLoading(false);
    }
  };

  const loadSubmissions = async (reqId: number) => {
    try {
      setLoadingSubmissions(true);
      const subs = await fetchPortalSubmissions(reqId);
      setSubmissions(subs);
    } catch (err: any) {
      console.error("Failed to load submissions:", err);
    } finally {
      setLoadingSubmissions(false);
    }
  };

  const handleSelectReq = (reqId: number) => {
    setSelectedReqId(reqId);
    loadSubmissions(reqId);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <ErrorState message={error} onRetry={loadRequisitions} />
      </div>
    );
  }

  if (requisitions.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <EmptyState
          title="No Shortlists Yet"
          description="Your recruiting team has not submitted any candidate shortlists for your review yet."
          icon={<Briefcase className="w-8 h-8" />}
        />
      </div>
    );
  }

  const activeReq = requisitions.find((r) => r.id === selectedReqId);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 md:py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Client Review Portal</h1>
        <p className="text-sm text-gray-600 mt-1">
          Review candidates shortlisted by your recruiting team, evaluate evidence, and record hiring decisions.
        </p>
      </div>

      {/* Role Selection Tabs (Mobile friendly horizontal scroll) */}
      <div className="flex gap-2 overflow-x-auto pb-3 mb-6 border-b border-gray-200">
        {requisitions.map((req) => (
          <button
            key={req.id}
            onClick={() => handleSelectReq(req.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              selectedReqId === req.id
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            <span>{req.title}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                selectedReqId === req.id ? "bg-blue-700 text-white" : "bg-gray-100 text-gray-600"
              }`}
            >
              {req.submission_count}
            </span>
          </button>
        ))}
      </div>

      {/* Active Role Submissions Header */}
      {activeReq && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">{activeReq.title}</h2>
              <Badge variant="default" size="sm">
                {activeReq.status}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              {submissions.length} candidate{submissions.length === 1 ? "" : "s"} submitted for review
            </p>
          </div>
          <div className="text-xs text-gray-500 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Candidate contacts are masked until shortlisted</span>
          </div>
        </div>
      )}

      {/* Submissions List */}
      {loadingSubmissions ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : submissions.length === 0 ? (
        <EmptyState
          title="No candidates submitted for this role"
          description="Candidates submitted by recruiters will appear here for review."
          icon={<UserCheck className="w-8 h-8" />}
        />
      ) : (
        <div className="space-y-3">
          {submissions.map((sub) => {
            const isShortlisted = sub.stage === "client_shortlisted" || sub.stage === "interview";
            const isRejected = sub.stage === "rejected";

            return (
              <div
                key={sub.submission_id}
                className="bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 pt-0.5">
                    {sub.weighted_score !== null ? (
                      <ScoreRing score={Math.round(sub.weighted_score)} size={48} />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-xs font-semibold text-gray-400">
                        N/A
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-base font-bold text-gray-900">{sub.candidate_name}</h3>
                      {isShortlisted && (
                        <Badge variant="success" size="sm">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Shortlisted</span>
                        </Badge>
                      )}
                      {isRejected && (
                        <Badge variant="danger" size="sm">
                          <XCircle className="w-3 h-3 text-rose-600" />
                          <span>Rejected</span>
                        </Badge>
                      )}
                      {!isShortlisted && !isRejected && (
                        <Badge variant="info" size="sm">
                          <Clock className="w-3 h-3 text-blue-600" />
                          <span>Pending Review</span>
                        </Badge>
                      )}
                    </div>

                    <div className="text-xs text-gray-500 mt-1 flex items-center gap-3 flex-wrap">
                      <span>Submitted: {new Date(sub.submitted_at).toLocaleDateString()}</span>
                      <span>Email: {sub.candidate_email}</span>
                      <span>Phone: {sub.candidate_phone}</span>
                    </div>

                    {/* Must-have gaps badge */}
                    {sub.must_have_gaps && sub.must_have_gaps.length > 0 && (
                      <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                        <span className="text-[11px] font-medium text-amber-700 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          Must-have gaps:
                        </span>
                        {sub.must_have_gaps.map((gap, i) => (
                          <span
                            key={i}
                            className="text-[11px] bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 rounded"
                          >
                            {gap}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-end">
                  <Link
                    to={`/portal/submissions/${sub.submission_id}`}
                    className="w-full md:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
                  >
                    <span>Review Candidate</span>
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
