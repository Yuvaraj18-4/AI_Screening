import React from "react";
import { Info } from "lucide-react";
import { useHealth } from "../api/auth";

export const HeuristicBanner: React.FC = () => {
  const { data: health } = useHealth();

  if (!health || health.scoring_mode !== "heuristic") {
    return null;
  }

  return (
    <div className="bg-amber-500/10 border-b border-amber-300/40 px-4 py-2 text-xs text-amber-900 flex items-center justify-center gap-2 font-medium">
      <Info className="w-4 h-4 text-amber-600 shrink-0" />
      <span>
        <strong>Heuristic Screening Mode Active:</strong> Operating without GEMINI_API_KEY. Rule-based evaluation with verified keyword evidence is in effect.
      </span>
    </div>
  );
};
