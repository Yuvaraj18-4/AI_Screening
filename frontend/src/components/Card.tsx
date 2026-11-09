import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className = "", onClick }) => {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-lg border border-gray-200 shadow-xs transition-shadow ${
        onClick ? "cursor-pointer hover:shadow-sm" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
};
