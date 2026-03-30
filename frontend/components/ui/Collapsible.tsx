"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { clsx } from "clsx";

type Props = Readonly<{
  header: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  headerClassName?: string;
}>;

export default function Collapsible({
  header,
  children,
  defaultOpen = true,
  className,
  headerClassName,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          "flex items-center gap-2 w-full text-left",
          headerClassName
        )}
        aria-expanded={open}
      >
        {header}
        {open ? (
          <ChevronDown className="ml-auto w-4 h-4 shrink-0" />
        ) : (
          <ChevronRight className="ml-auto w-4 h-4 shrink-0" />
        )}
      </button>
      {open && children}
    </div>
  );
}
