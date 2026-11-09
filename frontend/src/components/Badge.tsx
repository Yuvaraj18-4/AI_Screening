import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "info" | "outline";
  size?: "sm" | "md";
  className?: string;
  title?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
  size = "md",
  className = "",
  title,
}) => {
  const sizeStyles = {
    sm: "px-1.5 py-0.5 text-xs font-medium",
    md: "px-2.5 py-1 text-xs font-semibold",
  };

  const variantStyles = {
    default: "bg-gray-100 text-gray-800 border border-gray-200",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border border-amber-200",
    danger: "bg-red-50 text-red-700 border border-red-200",
    info: "bg-blue-50 text-blue-700 border border-blue-200",
    outline: "border border-gray-300 text-gray-700 bg-white",
  };

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
};
