import React, { useState, useEffect } from "react";
import { Sparkles, Plus, Trash2, Save, AlertCircle, CheckCircle } from "lucide-react";
import { type Criterion, useScorecard, useSaveScorecard } from "../../api/scorecards";
import { useExtractJD, useRequisition } from "../../api/requisitions";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import { Skeleton } from "../../components/Skeleton";
import { ErrorState } from "../../components/ErrorState";

interface ScorecardEditorProps {
  requisitionId: number;
}

export const ScorecardEditor: React.FC<ScorecardEditorProps> = ({ requisitionId }) => {
  const { data: requisition } = useRequisition(requisitionId);
  const { data: scorecard, isLoading, isError, refetch } = useScorecard(requisitionId);
  const saveMutation = useSaveScorecard(requisitionId);
  const extractMutation = useExtractJD(requisitionId);

  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    if (scorecard?.criteria) {
      setCriteria(scorecard.criteria);
    }
  }, [scorecard]);

  const handleExtract = async () => {
    setNotification(null);
    try {
      const res = await extractMutation.mutateAsync();
      if (res.criteria && res.criteria.length > 0) {
        setCriteria(res.criteria);
        setNotification({
          type: "success",
          message: `Extracted ${res.criteria.length} criteria from Job Description. Review and save below.`,
        });
      }
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to extract criteria from Job Description",
      });
    }
  };

  const handleAddCriterion = () => {
    setCriteria([
      ...criteria,
      {
        name: "New Skill",
        kind: "skill",
        must_have: false,
        weight: 3,
        params: { skill: "New Skill" },
        description: "",
      },
    ]);
  };

  const handleRemoveCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const handleUpdateCriterion = (index: number, patch: Partial<Criterion>) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], ...patch };
    setCriteria(updated);
  };

  const handleSave = async () => {
    setNotification(null);
    if (criteria.length === 0) {
      setNotification({ type: "error", message: "Scorecard must have at least one criterion" });
      return;
    }
    try {
      await saveMutation.mutateAsync(criteria);
      setNotification({ type: "success", message: "New scorecard version saved successfully!" });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Failed to save scorecard" });
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Could not load scorecard"
        message="Failed to retrieve scorecard for this requisition."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-lg border border-gray-200 shadow-xs">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-gray-900">Scorecard Definition</h2>
            {scorecard ? (
              <Badge variant="info" size="sm">
                Active Version v{scorecard.version}
              </Badge>
            ) : (
              <Badge variant="default" size="sm">
                Unsaved Draft
              </Badge>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1 max-w-xl">
            Deterministic criteria (experience, notice, location) are evaluated in code. Semantic criteria (skills, domain) are evaluated by AI with quote verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {requisition?.jd_text && (
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Sparkles className="w-4 h-4 text-purple-600" />}
              onClick={handleExtract}
              isLoading={extractMutation.isPending}
            >
              Extract from JD
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Save className="w-4 h-4" />}
            onClick={handleSave}
            isLoading={saveMutation.isPending}
          >
            Save as New Version
          </Button>
        </div>
      </div>

      {notification && (
        <div
          className={`p-4 rounded-md border flex items-start gap-2.5 text-sm ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {criteria.length === 0 ? (
        <div className="bg-white p-8 text-center rounded-lg border border-dashed border-gray-300">
          <p className="text-sm text-gray-500 mb-4">
            No criteria defined yet. Click "Extract from JD" to draft automatically, or add manually.
          </p>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={handleAddCriterion}
          >
            Add First Criterion
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {criteria.map((crit, idx) => (
            <Card key={idx} className="p-4 bg-white">
              <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
                <div className="md:col-span-4">
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase">
                    Criterion Name
                  </label>
                  <input
                    type="text"
                    value={crit.name}
                    onChange={(e) => handleUpdateCriterion(idx, { name: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 font-medium"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase">
                    Kind
                  </label>
                  <select
                    value={crit.kind}
                    onChange={(e) =>
                      handleUpdateCriterion(idx, {
                        kind: e.target.value as Criterion["kind"],
                      })
                    }
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="experience">Experience (Code)</option>
                    <option value="notice">Notice Period (Code)</option>
                    <option value="location">Location (Code)</option>
                    <option value="skill">Skill (AI)</option>
                    <option value="domain">Domain (AI)</option>
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-[10px] font-semibold text-gray-500 uppercase">
                    Weight (1-5)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={crit.weight}
                    onChange={(e) =>
                      handleUpdateCriterion(idx, {
                        weight: Math.max(1, Math.min(5, Number(e.target.value))),
                      })
                    }
                    className="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="md:col-span-2 flex items-center pt-3 gap-2">
                  <input
                    type="checkbox"
                    id={`must_have_${idx}`}
                    checked={crit.must_have}
                    onChange={(e) => handleUpdateCriterion(idx, { must_have: e.target.checked })}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 h-4 w-4"
                  />
                  <label
                    htmlFor={`must_have_${idx}`}
                    className="text-xs font-semibold text-gray-700 select-none cursor-pointer"
                  >
                    Must-Have
                  </label>
                </div>

                <div className="md:col-span-2 flex justify-end pt-3">
                  <button
                    type="button"
                    onClick={() => handleRemoveCriterion(idx)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Remove Criterion"
                    aria-label="Remove Criterion"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="mt-2 pt-2 border-t border-gray-100">
                <input
                  type="text"
                  placeholder="Optional description / details..."
                  value={crit.description}
                  onChange={(e) => handleUpdateCriterion(idx, { description: e.target.value })}
                  className="w-full px-2 py-1 text-xs text-gray-600 border border-transparent hover:border-gray-200 focus:border-gray-300 rounded focus:outline-hidden"
                />
              </div>
            </Card>
          ))}

          <Button
            variant="outline"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={handleAddCriterion}
            className="w-full py-2.5"
          >
            Add Criterion
          </Button>
        </div>
      )}
    </div>
  );
};
