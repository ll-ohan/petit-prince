"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import type { Step } from "@/types/message";
import Collapsible from "@/components/ui/Collapsible";
import ToolCallBlock from "./ToolCallBlock";

type Props = Readonly<{
  steps: readonly Step[];
  isLive: boolean;
}>;

export default function ThinkingPanel({ steps, isLive }: Props) {
  if (steps.length === 0) return null;

  const header = (
    <>
      {isLive ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <CheckCircle2 className="w-4 h-4 text-green-500" />
      )}
      <span className={clsx("text-sm font-medium", isLive && "animate-pulse")}>
        {isLive ? "Réflexion en cours..." : "Réflexion terminée"}
      </span>
    </>
  );

  return (
    <Collapsible
      header={header}
      defaultOpen={true}
      className="my-4 border-l-2 border-dark/80 bg-white/30 rounded-r-lg overflow-hidden"
      headerClassName="p-3 text-accent hover:bg-accent/5 transition-colors"
    >
      <div className="p-3 pt-0 space-y-2 text-sm text-slate-600 leading-relaxed">
        {steps.map((step) => {
          switch (step.type) {
            case "thinking":
              return (
                <div key={step.id} className="italic text-xs">
                  {step.content}
                </div>
              );
            case "tool_call":
              return <ToolCallBlock key={step.id} toolCall={step} />;
            default:
              return null;
          }
        })}
      </div>
    </Collapsible>
  );
}