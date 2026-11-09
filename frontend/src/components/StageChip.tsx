import React from "react";
import {
  CheckCircle2,
  Clock,
  Send,
  UserCheck,
  Calendar,
  Award,
  Sparkles,
  XCircle,
} from "lucide-react";
import { Badge } from "./Badge";

interface StageChipProps {
  stage: string;
}

export const StageChip: React.FC<StageChipProps> = ({ stage }) => {
  switch (stage) {
    case "sourced":
      return (
        <Badge variant="default" size="sm">
          <Clock className="w-3 h-3 text-gray-500" />
          <span>Sourced</span>
        </Badge>
      );
    case "screened":
      return (
        <Badge variant="info" size="sm">
          <Sparkles className="w-3 h-3 text-blue-500" />
          <span>Screened</span>
        </Badge>
      );
    case "submitted":
      return (
        <Badge variant="warning" size="sm">
          <Send className="w-3 h-3 text-amber-500" />
          <span>Submitted</span>
        </Badge>
      );
    case "client_shortlisted":
      return (
        <Badge variant="success" size="sm">
          <UserCheck className="w-3 h-3 text-emerald-500" />
          <span>Shortlisted</span>
        </Badge>
      );
    case "interview":
      return (
        <Badge variant="info" size="sm">
          <Calendar className="w-3 h-3 text-blue-500" />
          <span>Interview</span>
        </Badge>
      );
    case "offered":
      return (
        <Badge variant="success" size="sm">
          <Award className="w-3 h-3 text-emerald-600" />
          <span>Offered</span>
        </Badge>
      );
    case "joined":
      return (
        <Badge variant="success" size="sm">
          <CheckCircle2 className="w-3 h-3 text-emerald-700" />
          <span>Joined</span>
        </Badge>
      );
    case "rejected":
      return (
        <Badge variant="danger" size="sm">
          <XCircle className="w-3 h-3 text-red-500" />
          <span>Rejected</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="default" size="sm">
          <span>{stage}</span>
        </Badge>
      );
  }
};
