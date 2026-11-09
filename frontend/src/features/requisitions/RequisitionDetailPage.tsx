import React, { useState, useEffect } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Sliders, Upload, Users, Kanban } from "lucide-react";
import { useRequisition } from "../../api/requisitions";
import { ScorecardEditor } from "../scorecard/ScorecardEditor";
import { UploadPage } from "../uploads/UploadPage";
import { CandidateRankedList } from "../candidates/CandidateRankedList";
import { PipelineBoard } from "../pipeline/PipelineBoard";
import { Badge } from "../../components/Badge";
import { Skeleton } from "../../components/Skeleton";
import { ErrorState } from "../../components/ErrorState";

export const RequisitionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const reqId = Number(id);
  const { data: requisition, isLoading, isError, refetch } = useRequisition(reqId);
  const paramTab = searchParams.get("tab") as "scorecard" | "upload" | "candidates" | "pipeline" | null;
  const [activeTab, setActiveTab] = useState<"scorecard" | "upload" | "candidates" | "pipeline">(
    paramTab && ["scorecard", "upload", "candidates", "pipeline"].includes(paramTab) ? paramTab : "candidates"
  );

  useEffect(() => {
    if (paramTab && ["scorecard", "upload", "candidates", "pipeline"].includes(paramTab)) {
      setActiveTab(paramTab);
    }
  }, [paramTab]);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-12 w-3/4" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !requisition) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorState
          title="Requisition not found"
          message="Could not load details for this requisition."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Breadcrumb & Title */}
      <div className="mb-6">
        <Link
          to="/requisitions"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-900 mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Requisitions</span>
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                {requisition.title}
              </h1>
              <Badge variant={requisition.status === "active" ? "success" : "default"}>
                {requisition.status}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Client: <strong>{requisition.client_name || `Client #${requisition.client_id}`}</strong>
              {requisition.active_scorecard_version && (
                <span className="ml-3">
                  Scorecard: <strong>v{requisition.active_scorecard_version}</strong>
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab("candidates")}
            className={`flex items-center gap-2 py-3 px-1 border-b-2 font-medium text-sm transition-colors cursor-pointer ${
              activeTab === "candidates"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Candidates</span>
            <span className="ml-1.5 py-0.5 px-2 rounded-full text-xs bg-gray-100 text-gray-700">
              {requisition.applications_count}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("scorecard")}
            className={`flex items-center gap-2 py-3 px-1 border-b-2 font-medium text-sm transition-colors cursor-pointer ${
              activeTab === "scorecard"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Scorecard</span>
          </button>

          <button
            onClick={() => setActiveTab("upload")}
            className={`flex items-center gap-2 py-3 px-1 border-b-2 font-medium text-sm transition-colors cursor-pointer ${
              activeTab === "upload"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Bulk Upload</span>
          </button>

          <button
            onClick={() => setActiveTab("pipeline")}
            className={`flex items-center gap-2 py-3 px-1 border-b-2 font-medium text-sm transition-colors cursor-pointer ${
              activeTab === "pipeline"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Kanban className="w-4 h-4" />
            <span>Pipeline Board</span>
          </button>
        </nav>
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === "candidates" && <CandidateRankedList requisitionId={reqId} />}
        {activeTab === "scorecard" && <ScorecardEditor requisitionId={reqId} />}
        {activeTab === "upload" && <UploadPage requisitionId={reqId} onUploadDone={() => setActiveTab("candidates")} />}
        {activeTab === "pipeline" && <PipelineBoard requisitionId={reqId} />}
      </div>
    </div>
  );
};
