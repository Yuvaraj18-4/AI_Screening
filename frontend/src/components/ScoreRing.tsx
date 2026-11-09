import React from "react";

interface ScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

export const ScoreRing: React.FC<ScoreRingProps> = ({
  score,
  size = 48,
  strokeWidth = 4,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));
  const offset = circumference - (clampedScore / 100) * circumference;

  let colorClass = "text-emerald-600";
  if (clampedScore < 50) colorClass = "text-red-500";
  else if (clampedScore < 75) colorClass = "text-amber-500";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-100"
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${colorClass} transition-all duration-500 ease-out`}
          fill="transparent"
        />
      </svg>
      <span className="absolute text-xs font-bold text-gray-800">
        {clampedScore}
      </span>
    </div>
  );
};
