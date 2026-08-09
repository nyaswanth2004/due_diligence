import * as React from "react";
import { cn } from "../../lib/utils";

export function Avatar({
  name,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { name: string }) {
  const initials = name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return (
    <div
      className={cn(
        "flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-primary to-emerald-500 text-xs font-semibold text-white shadow-lg shadow-primary/20",
        className
      )}
      {...props}
    >
      {initials || "?"}
    </div>
  );
}
