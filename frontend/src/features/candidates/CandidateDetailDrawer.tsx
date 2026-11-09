import React, { useState } from "react";
import {
  X,
  Send,
  RefreshCw,
  AlertCircle,
  Briefcase,
  MapPin,
  Clock,
  GraduationCap,
  FileText,
  Shield,
  Layers,
  CheckCircle2,
} from "lucide-react";
import {
  useApplicationDetail,
  useSubmitApplication,
  useRescoreApplication,
} from "../../api/candidates";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { ScoreRing } from "../../components/ScoreRing";
import { StageChip } from "../../components/StageChip";
import { EvidenceItem } from "../../components/EvidenceItem";
import { Skeleton } from "../../components/Skeleton";
import { ErrorState } from "../../components/ErrorState";

interface CandidateDetailDrawerProps {
  applicationId: number | null;
  onClose: () => void;
  requisitionId: number;
}

export const CandidateDetailDrawer: React.FC<CandidateDetailDrawerProps> = ({
  applicationId,
  onClose,
  requisitionId,
}) => {
  const { data: application, isLoading, isError, refetch } = useApplicationDetail(applicationId);
  const submitMutation = useSubmitApplication(requisitionId);
  const rescoreMutation = useRescoreApplication(requisitionId);

  const [activeTab, setActiveTab] = useState<"evidence" | "profile" | "masked_text">("evidence");
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState(false);

  if (!applicationId) return null;

  const handleSubmit = async () => {
    setSubmitError("");
    setSubmitSuccess(false);
    try {
      await submitMutation.mutateAsync(applicationId);
      setSubmitSuccess(true);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to submit candidate to client");
    }
  };

  const handleRescore = async () => {
    try {
      await rescoreMutation.mutateAsync(applicationId);
    } catch (err: any) {
      alert(err.message || "Failed to rescore application");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
      <div className="w-full max-w-3xl bg-white h-full shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-gray-900">Candidate Evaluation</h2>
            {application && <StageChip stage={application.stage} />}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Loading / Error States */}
        {isLoading && (
          <div className="p-8 space-y-4 flex-1">
            <Skeleton className="h-10 w-1/2" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        )}

        {isError && (
          <div className="p-8 flex-1">
            <ErrorState
              title="Could not load candidate details"
              message="Failed to fetch candidate screening information."
              onRetry={() => refetch()}
            />
          </div>
        )}

        {/* Content */}
        {!isLoading && !isError && application && (
          <div className="flex-1 overflow-y-auto">
            {/* Candidate Summary Card */}
            <div className="p-6 bg-gray-50 border-b border-gray-200">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-bold text-gray-900">
                      {application.candidate_name}
                    </h3>
                    {application.duplicate_of_id && (
                      <Badge variant="warning" size="sm">
                        Duplicate Profile
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs font-semibold text-gray-600 flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-gray-400" />
                    <span>{application.current_role}</span>
                  </p>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 pt-1">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-gray-400" />
                      {application.location || "Location not specified"}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-gray-400" />
                      {application.experience_years} yrs exp
                    </span>
                    <span>•</span>
                    <span>Notice: <strong>{application.notice_days} days</strong></span>
                  </div>
                </div>

                {/* Score Ring & Action */}
                <div className="flex items-center gap-4">
                  {application.score && (
                    <div className="flex items-center gap-3 bg-white px-3 py-2 rounded-lg border border-gray-200 shadow-xs">
                      <ScoreRing score={application.score.total} size={50} strokeWidth={5} />
                      <div className="flex flex-col">
                        <span className="text-[10px] font-semibold text-gray-400 uppercase">
                          Match Score
                        </span>
                        <span className="text-xs font-bold text-gray-800">
                          {application.score.confidence.toUpperCase()} CONFIDENCE
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-col gap-1.5">
                    {application.stage !== "submitted" && application.stage !== "client_shortlisted" ? (
                      <Button
                        variant="primary"
                        size="sm"
                        leftIcon={<Send className="w-4 h-4" />}
                        onClick={handleSubmit}
                        isLoading={submitMutation.isPending}
                      >
                        Submit to Client
                      </Button>
                    ) : (
                      <Badge variant="info" size="md">
                        Submitted to Client
                      </Badge>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                      onClick={handleRescore}
                      isLoading={rescoreMutation.isPending}
                    >
                      Rescore
                    </Button>
                  </div>
                </div>
              </div>

              {/* Must Have Gaps Alert */}
              {application.score && application.score.must_have_gaps.length > 0 && (
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md flex items-start gap-2.5 text-xs text-amber-900">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Must-Have Criteria Gaps Detected: </span>
                    <span>Candidate does not fully satisfy: </span>
                    <strong className="underline">{application.score.must_have_gaps.join(", ")}</strong>.
                    <span className="ml-1 text-gray-600">(Not auto-rejected; review evidence below).</span>
                  </div>
                </div>
              )}

              {submitError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2 text-xs text-red-700">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{submitError}</span>
                </div>
              )}

              {submitSuccess && (
                <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-md flex items-start gap-2 text-xs text-emerald-800">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span>Candidate successfully submitted to client review portal!</span>
                </div>
              )}
            </div>

            {/* Navigation Tabs */}
            <div className="border-b border-gray-200 px-6 bg-white">
              <nav className="flex space-x-6 text-xs font-semibold" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab("evidence")}
                  className={`py-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                    activeTab === "evidence"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>Evidence Drawer</span>
                </button>

                <button
                  onClick={() => setActiveTab("profile")}
                  className={`py-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                    activeTab === "profile"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Profile & Employment</span>
                </button>

                <button
                  onClick={() => setActiveTab("masked_text")}
                  className={`py-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                    activeTab === "masked_text"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Masked Resume Text</span>
                </button>
              </nav>
            </div>

            {/* Tab Contents */}
            <div className="p-6">
              {activeTab === "evidence" && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                    Criteria Score Breakdown & Verified Quotes
                  </h4>
                  {application.score?.results && application.score.results.length > 0 ? (
                    application.score.results.map((res) => (
                      <EvidenceItem key={res.id} result={res} />
                    ))
                  ) : (
                    <p className="text-xs text-gray-400 italic">No score results available.</p>
                  )}
                </div>
              )}

              {activeTab === "profile" && (
                <div className="space-y-6">
                  {/* Skills tags */}
                  <div>
                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                      Extracted Skills
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {application.skills?.map((sk, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-medium"
                        >
                          {sk}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Employment History */}
                  <div>
                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                      Employment Timeline
                    </h4>
                    <div className="space-y-3 border-l-2 border-gray-200 pl-4">
                      {application.employment?.map((emp, i) => (
                        <div key={i} className="relative space-y-0.5">
                          <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 bg-blue-600 rounded-full border-2 border-white" />
                          <h5 className="text-xs font-bold text-gray-900">{emp.title}</h5>
                          <p className="text-xs text-gray-600 font-medium">{emp.company}</p>
                          <p className="text-[11px] text-gray-400">
                            {emp.start || "Start"} — {emp.end || "End"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Education */}
                  {application.education?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                        Education
                      </h4>
                      <div className="space-y-2">
                        {application.education.map((edu, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-gray-700">
                            <GraduationCap className="w-4 h-4 text-gray-400 shrink-0" />
                            <span>
                              <strong>{edu.degree || "Degree"}</strong>, {edu.institution || "University"} ({edu.year || ""})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "masked_text" && (
                <div className="space-y-3">
                  <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-md text-xs text-blue-900">
                    <p className="font-semibold mb-0.5">Fairness & Privacy Masking Active</p>
                    <p className="text-[11px] text-blue-700">
                      Personal names, email, phone, personal titles, DOB, and gendered pronouns were redacted prior to AI evaluation to promote fairness.
                    </p>
                  </div>
                  <pre className="p-4 bg-gray-900 text-gray-100 rounded-lg text-xs font-mono whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                    {application.masked_text || application.cv_text || "No text available."}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
