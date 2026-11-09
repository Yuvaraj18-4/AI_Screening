import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Briefcase, Users, FileText, ChevronRight, AlertCircle } from "lucide-react";
import { useRequisitions, useCreateRequisition } from "../../api/requisitions";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import { Skeleton } from "../../components/Skeleton";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Dialog } from "../../components/Dialog";

export const RequisitionListPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: requisitions, isLoading, isError, refetch } = useRequisitions();
  const createReqMutation = useCreateRequisition();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [clientId, setClientId] = useState(1);
  const [title, setTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [modalError, setModalError] = useState("");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError("");
    if (!title.trim()) {
      setModalError("Job title is required");
      return;
    }
    try {
      const created = await createReqMutation.mutateAsync({
        client_id: clientId,
        title: title.trim(),
        jd_text: jdText.trim(),
      });
      setIsModalOpen(false);
      setTitle("");
      setJdText("");
      navigate(`/requisitions/${created.id}`);
    } catch (err: any) {
      setModalError(err.message || "Failed to create requisition");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Job Requisitions
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage hiring requirements, scorecards, candidate pipelines and submissions.
          </p>
        </div>
        <Button
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => setIsModalOpen(true)}
        >
          New Requisition
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {isError && (
        <ErrorState
          title="Could not load requisitions"
          message="Failed to fetch job requisitions. Please check if backend is running."
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && requisitions?.length === 0 && (
        <EmptyState
          title="No requisitions found"
          description="Create your first job requisition with a Job Description to start screening candidates."
          icon={<Briefcase className="w-8 h-8 text-blue-500" />}
          action={
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setIsModalOpen(true)}
            >
              Create Requisition
            </Button>
          }
        />
      )}

      {!isLoading && !isError && requisitions && requisitions.length > 0 && (
        <div className="space-y-3">
          {requisitions.map((req) => (
            <Card
              key={req.id}
              className="p-5 hover:border-blue-300 transition-colors"
              onClick={() => navigate(`/requisitions/${req.id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-base font-semibold text-gray-900">
                      {req.title}
                    </h2>
                    <Badge
                      variant={req.status === "active" ? "success" : "default"}
                      size="sm"
                    >
                      {req.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Client: <strong>{req.client_name || `Client #${req.client_id}`}</strong></span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3.5 h-3.5 text-gray-400" />
                      {req.applications_count} candidate{req.applications_count === 1 ? "" : "s"}
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-gray-400" />
                      Scorecard: {req.active_scorecard_version ? `v${req.active_scorecard_version}` : "Draft"}
                    </span>
                  </div>
                </div>
                <div className="flex items-center text-gray-400">
                  <ChevronRight className="w-5 h-5" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create Requisition Dialog */}
      <Dialog
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Job Requisition"
        maxWidth="lg"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {modalError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{modalError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              Client Organization
            </label>
            <select
              value={clientId}
              onChange={(e) => setClientId(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={1}>Apex Financial Technologies (Client 1)</option>
              <option value={2}>Zenith Retail Solutions (Client 2)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              Job Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Senior Java Developer"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              Job Description (JD Text)
            </label>
            <textarea
              rows={6}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste job description text here to automatically extract screening criteria..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={createReqMutation.isPending}
            >
              Create Requisition
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
};
