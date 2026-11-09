import React from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = "",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed";

  const sizeStyles = {
    sm: "px-2.5 py-1.5 text-xs gap-1.5",
    md: "px-3.5 py-2 text-sm gap-2",
    lg: "px-4 py-2.5 text-base gap-2.5",
  };

  const variantStyles = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 focus-visible:outline-blue-600",
    secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200 active:bg-gray-300",
    outline: "border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 active:bg-gray-100",
    danger: "bg-red-600 text-white hover:bg-red-700 active:bg-red-800 focus-visible:outline-red-600",
    ghost: "text-gray-600 hover:bg-gray-100 active:bg-gray-200",
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : leftIcon}
      {children}
      {!isLoading && rightIcon}
    </button>
  );
};
