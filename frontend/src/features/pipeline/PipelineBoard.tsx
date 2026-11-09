import React, { useEffect, useState } from "react";
import {
  Users,
  AlertTriangle,
} from "lucide-react";
import {
  fetchApplications,
  updateApplicationStage,
  type ApplicationListItem,
} from "../../api/candidates";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { ScoreRing } from "../../components/ScoreRing";
import { Skeleton } from "../../components/Skeleton";
import { CandidateDetailDrawer } from "../candidates/CandidateDetailDrawer";

interface PipelineBoardProps {
  requisitionId: number;
}

const STAGES = [
  { id: "sourced", label: "Sourced", color: "bg-slate-50 border-slate-200 text-slate-700" },
  { id: "screened", label: "Screened", color: "bg-sky-50 border-sky-200 text-sky-700" },
  { id: "submitted", label: "Submitted", color: "bg-blue-50 border-blue-200 text-blue-700" },
  { id: "client_shortlisted", label: "Shortlisted", color: "bg-purple-50 border-purple-200 text-purple-700" },
  { id: "interview", label: "Interview", color: "bg-indigo-50 border-indigo-200 text-indigo-700" },
  { id: "offered", label: "Offered", color: "bg-emerald-50 border-emerald-200 text-emerald-700" },
  { id: "joined", label: "Joined", color: "bg-green-50 border-green-200 text-green-700" },
  { id: "rejected", label: "Rejected", color: "bg-rose-50 border-rose-200 text-rose-700" },
] as const;

export const PipelineBoard: React.FC<PipelineBoardProps> = ({ requisitionId }) => {
  const [applications, setApplications] = useState<ApplicationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  useEffect(() => {
    loadPipeline();
  }, [requisitionId]);

  const loadPipeline = async () => {
    try {
      setLoading(true);
      setError(null);
      const apps = await fetchApplications(requisitionId, { sort: "score" });
      setApplications(apps);
    } catch (err: any) {
      setError(err?.message || "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  };

  const handleStageChange = async (appId: number, newStage: string) => {
    try {
      setUpdatingId(appId);
      await updateApplicationStage(appId, newStage);
      setApplications((prev) =>
        prev.map((app) => (app.id === appId ? { ...app, stage: newStage } : app))
      );
    } catch (err: any) {
      alert(err?.message || "Failed to update stage");
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4">
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <ErrorState message={error} onRetry={loadPipeline} />
      </div>
    );
  }

  if (applications.length === 0) {
    return (
      <div className="p-6">
        <EmptyState
          title="No candidates in pipeline"
          description="Upload resumes in the Bulk Upload tab to populate this requisition's hiring pipeline."
          icon={<Users className="w-8 h-8" />}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Board Summary Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-900">Hiring Pipeline</span>
          <span className="text-xs text-gray-500">
            ({applications.length} candidate{applications.length === 1 ? "" : "s"})
          </span>
        </div>
        <span className="text-xs text-gray-400">Click candidate to view evidence • Use dropdown to advance stage</span>
      </div>

      {/* Horizontal scrolling Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-6 pt-1">
        {STAGES.map((stage) => {
          const stageApps = applications.filter((a) => a.stage === stage.id);

          return (
            <div
              key={stage.id}
              className="flex-shrink-0 w-72 bg-gray-50/75 rounded-xl border border-gray-200 flex flex-col max-h-[750px]"
            >
              {/* Column Header */}
              <div className="p-3 border-b border-gray-200 flex items-center justify-between bg-white rounded-t-xl">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-gray-800 uppercase tracking-wider">
                    {stage.label}
                  </span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                    {stageApps.length}
                  </span>
                </div>
              </div>

              {/* Column Cards Container */}
              <div className="p-2 space-y-2.5 overflow-y-auto flex-1">
                {stageApps.length === 0 ? (
                  <div className="py-8 text-center text-xs text-gray-400 font-medium border-2 border-dashed border-gray-200/60 rounded-lg">
                    Empty stage
                  </div>
                ) : (
                  stageApps.map((app) => (
                    <div
                      key={app.id}
                      className="bg-white rounded-lg border border-gray-200 hover:border-blue-400 hover:shadow-md transition-all p-3 cursor-pointer group shadow-sm"
                      onClick={() => setSelectedAppId(app.id)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                            {app.candidate_name}
                          </h4>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {app.experience_years}y exp • {app.notice_days}d notice
                          </p>
                        </div>
                        {app.score && (
                          <div className="flex-shrink-0">
                            <ScoreRing score={Math.round(app.score.total)} size={40} />
                          </div>
                        )}
                      </div>

                      {/* Must-have gaps chip */}
                      {app.score?.must_have_gaps && app.score.must_have_gaps.length > 0 && (
                        <div className="mt-2">
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                            <AlertTriangle className="w-3 h-3" />
                            <span>{app.score.must_have_gaps.length} gap(s)</span>
                          </span>
                        </div>
                      )}

                      {/* Stage Transition Control */}
                      <div
                        className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-xs"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span className="text-gray-400 text-[11px] font-medium">Stage:</span>
                        <select
                          value={app.stage}
                          onChange={(e) => handleStageChange(app.id, e.target.value)}
                          disabled={updatingId === app.id}
                          className="text-xs bg-gray-50 border border-gray-200 rounded px-1.5 py-1 text-gray-700 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          {STAGES.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Candidate Detail Drawer */}
      {selectedAppId !== null && (
        <CandidateDetailDrawer
          applicationId={selectedAppId}
          requisitionId={requisitionId}
          onClose={() => {
            setSelectedAppId(null);
            loadPipeline();
          }}
        />
      )}
    </div>
  );
};
