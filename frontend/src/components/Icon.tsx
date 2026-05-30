import type { LucideIcon } from "lucide-react";

const SIZES = {
  sm: 12,
  md: 14,
  lg: 18,
  xl: 20,
} as const;

interface IconProps {
  icon: LucideIcon;
  size?: keyof typeof SIZES;
  className?: string;
}

export function Icon({ icon: Component, size = "md", className }: IconProps) {
  return (
    <Component
      size={SIZES[size]}
      className={className ? `icon ${className}` : "icon"}
      aria-hidden
    />
  );
}

export type { LucideIcon };
