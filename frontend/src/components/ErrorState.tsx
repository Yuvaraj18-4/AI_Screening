import React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message = "Failed to load data. Please check your connection and try again.",
  onRetry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-red-50/50 rounded-lg border border-red-200 my-4">
      <div className="p-3 bg-red-100 rounded-full text-red-600 mb-3">
        <AlertTriangle className="w-8 h-8" />
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-600 max-w-sm mb-4">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try Again
        </Button>
      )}
    </div>
  );
};
