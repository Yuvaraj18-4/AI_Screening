import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, ShieldAlert, Cpu, Code2 } from "lucide-react";
import type { CriterionResultDetail } from "../api/candidates";
import { Badge } from "./Badge";

interface EvidenceItemProps {
  result: CriterionResultDetail;
}

export const EvidenceItem: React.FC<EvidenceItemProps> = ({ result }) => {
  const getVerdictBadge = () => {
    switch (result.verdict) {
      case "met":
        return (
          <Badge variant="success" size="sm">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Met</span>
          </Badge>
        );
      case "partial":
        return (
          <Badge variant="warning" size="sm">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Partial</span>
          </Badge>
        );
      case "unverified":
        return (
          <Badge variant="danger" size="sm">
            <ShieldAlert className="w-3 h-3 text-red-600" />
            <span>Unverified Quote</span>
          </Badge>
        );
      case "not_found":
        return (
          <Badge variant="default" size="sm">
            <XCircle className="w-3 h-3 text-gray-500" />
            <span>Not Found</span>
          </Badge>
        );
      default:
        return (
          <Badge variant="default" size="sm">
            <span>{result.verdict}</span>
          </Badge>
        );
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200 space-y-2.5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-gray-900">
            {result.criterion_name}
          </span>
          {result.must_have && (
            <Badge variant="danger" size="sm">
              Must-Have
            </Badge>
          )}
          <span className="text-[11px] text-gray-400">
            Weight: {result.weight}x
          </span>
        </div>

        <div className="flex items-center gap-2">
          {getVerdictBadge()}
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-500">
            {result.source === "code" ? (
              <>
                <Code2 className="w-3 h-3 text-gray-400" />
                <span>Deterministic (Code)</span>
              </>
            ) : (
              <>
                <Cpu className="w-3 h-3 text-purple-400" />
                <span>AI Evaluated</span>
              </>
            )}
          </span>
        </div>
      </div>

      {/* Quote & Verification Callout */}
      {result.quote ? (
        <div className={`p-3 rounded-md text-xs border ${
          result.quote_verified
            ? "bg-gray-50 border-gray-200 text-gray-800"
            : "bg-red-50/70 border-red-200 text-red-900"
        }`}>
          <div className="flex items-center justify-between mb-1 text-[10px] uppercase tracking-wider font-semibold">
            <span className="text-gray-500">Extracted Quote from Resume</span>
            {result.quote_verified ? (
              <span className="inline-flex items-center gap-1 text-emerald-700">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Verified Substring</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-red-600">
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Unverified / Hallucination</span>
              </span>
            )}
          </div>
          <p className="italic font-serif leading-relaxed">
            "{result.quote}"
          </p>
        </div>
      ) : (
        <div className="text-xs text-gray-400 italic">
          No matching quote or evidence found in resume.
        </div>
      )}

      <div className="flex items-center justify-between text-[11px] text-gray-400 pt-1">
        <span>Confidence: {(result.confidence * 100).toFixed(0)}%</span>
        <span>Points: {(result.value * result.weight).toFixed(1)} / {result.weight}</span>
      </div>
    </div>
  );
};
