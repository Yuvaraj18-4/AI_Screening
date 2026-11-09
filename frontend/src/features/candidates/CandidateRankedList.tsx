import React, { useState } from "react";
import {
  Users,
  Search,
  Filter,
  Eye,
  AlertTriangle,
  Send,
  Copy,
  ChevronRight,
} from "lucide-react";
import { useApplications, useSubmitApplication } from "../../api/candidates";
import { CandidateDetailDrawer } from "./CandidateDetailDrawer";
import { ScoreRing } from "../../components/ScoreRing";
import { Badge } from "../../components/Badge";
import { StageChip } from "../../components/StageChip";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Skeleton } from "../../components/Skeleton";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";

interface CandidateRankedListProps {
  requisitionId: number;
}

export const CandidateRankedList: React.FC<CandidateRankedListProps> = ({ requisitionId }) => {
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [stageFilter, setStageFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: applications, isLoading, isError, refetch } = useApplications(
    requisitionId,
    sortBy,
    stageFilter,
  );

  const submitMutation = useSubmitApplication(requisitionId);

  const filteredApplications = applications?.filter((app) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      app.candidate_name.toLowerCase().includes(query) ||
      app.current_role.toLowerCase().includes(query) ||
      app.location.toLowerCase().includes(query)
    );
  });

  const handleQuickSubmit = async (e: React.MouseEvent, appId: number, hasViewed: boolean) => {
    e.stopPropagation();
    if (!hasViewed) {
      // Must open to view first
      setSelectedAppId(appId);
      return;
    }
    try {
      await submitMutation.mutateAsync(appId);
    } catch (err: any) {
      alert(err.message || "Failed to submit application");
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search candidates, roles, location..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <div className="flex items-center gap-1.5 text-xs text-gray-600">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="px-2 py-1 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Stages</option>
              <option value="sourced">Sourced</option>
              <option value="screened">Screened</option>
              <option value="submitted">Submitted</option>
              <option value="client_shortlisted">Client Shortlisted</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-gray-600">
            <span>Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-2 py-1 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500"
            >
              <option value="score">Rank (Score)</option>
              <option value="name">Name (A-Z)</option>
              <option value="stage">Stage</option>
            </select>
          </div>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {/* Error State */}
      {isError && (
        <ErrorState
          title="Could not load candidate list"
          message="Failed to fetch ranked candidates for this requisition."
          onRetry={() => refetch()}
        />
      )}

      {/* Empty State */}
      {!isLoading && !isError && filteredApplications?.length === 0 && (
        <EmptyState
          title="No candidates found"
          description="Upload resumes in the 'Bulk Upload' tab to start screening and ranking candidates."
          icon={<Users className="w-8 h-8 text-blue-500" />}
        />
      )}

      {/* Candidates List Table / Cards */}
      {!isLoading && !isError && filteredApplications && filteredApplications.length > 0 && (
        <div className="space-y-2">
          {filteredApplications.map((app, index) => {
            const scoreTotal = app.score?.total ?? 0;
            const hasGaps = (app.score?.must_have_gaps?.length ?? 0) > 0;
            const isTop3 = index < 3 && scoreTotal >= 70;

            return (
              <Card
                key={app.id}
                onClick={() => setSelectedAppId(app.id)}
                className={`p-4 transition-all duration-150 hover:border-blue-400 ${
                  isTop3 ? "border-l-4 border-l-blue-600" : ""
                } ${app.duplicate_of_id ? "bg-amber-50/20" : "bg-white"}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  {/* Left: Rank # & Candidate Details */}
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-xs font-bold text-gray-700 shrink-0">
                      {index + 1}
                    </span>

                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-gray-900 truncate">
                          {app.candidate_name}
                        </h4>

                        {/* Duplicate Icon */}
                        {app.duplicate_of_id && (
                          <span
                            className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200"
                            title="Duplicate candidate detected"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Duplicate</span>
                          </span>
                        )}

                        {/* Parse Quality Warning */}
                        {app.parse_quality < 0.6 && (
                          <span
                            className="inline-flex items-center gap-1 text-[11px] font-medium text-red-700 bg-red-50 px-1.5 py-0.5 rounded border border-red-200"
                            title="Low parsing quality: Scanned PDF or formatting irregularity"
                          >
                            <AlertTriangle className="w-3 h-3 text-red-500" />
                            <span>Scan / Low Quality</span>
                          </span>
                        )}

                        {app.score?.status === "ai_failed" && (
                          <Badge variant="danger" size="sm">
                            AI Failed (Retry)
                          </Badge>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                        <span className="font-medium text-gray-700">{app.current_role}</span>
                        <span>•</span>
                        <span>{app.experience_years} yrs exp</span>
                        <span>•</span>
                        <span>Notice: {app.notice_days}d</span>
                        {app.location && (
                          <>
                            <span>•</span>
                            <span>{app.location}</span>
                          </>
                        )}
                      </div>

                      {/* Must-Have Gap Badges */}
                      {hasGaps && app.score && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          {app.score.must_have_gaps.map((gap, gIdx) => (
                            <span
                              key={gIdx}
                              className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-800 bg-amber-100/70 px-2 py-0.5 rounded-full"
                            >
                              <AlertTriangle className="w-3 h-3 text-amber-600" />
                              <span>Gap: {gap}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right: Score Ring, Confidence, Stage & Actions */}
                  <div className="flex items-center gap-4 shrink-0 justify-between sm:justify-end border-t sm:border-t-0 pt-2 sm:pt-0">
                    {/* Score Ring */}
                    {app.score && (
                      <div className="flex items-center gap-2">
                        <ScoreRing score={scoreTotal} size={44} strokeWidth={4} />
                        <div className="flex flex-col text-right">
                          <span className="text-[10px] font-bold text-gray-500 uppercase">
                            {app.score.confidence}
                          </span>
                          <span className="text-[9px] text-gray-400">
                            {app.score.scoring_mode === "llm" ? "AI" : "Rules"}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Stage Chip */}
                    <StageChip stage={app.stage} />

                    {/* Action Button */}
                    <div className="flex items-center gap-1.5">
                      {app.stage !== "submitted" && app.stage !== "client_shortlisted" ? (
                        <Button
                          variant="outline"
                          size="sm"
                          leftIcon={app.has_viewed ? <Send className="w-3.5 h-3.5 text-blue-600" /> : <Eye className="w-3.5 h-3.5 text-gray-500" />}
                          onClick={(e) => handleQuickSubmit(e, app.id, app.has_viewed)}
                          title={app.has_viewed ? "Submit to client" : "Open and review CV first"}
                        >
                          {app.has_viewed ? "Submit" : "Review"}
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          leftIcon={<Eye className="w-3.5 h-3.5" />}
                          onClick={() => setSelectedAppId(app.id)}
                        >
                          View
                        </Button>
                      )}
                      <ChevronRight className="w-4 h-4 text-gray-300" />
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Candidate Detail Drawer */}
      <CandidateDetailDrawer
        applicationId={selectedAppId}
        requisitionId={requisitionId}
        onClose={() => setSelectedAppId(null)}
      />
    </div>
  );
};
