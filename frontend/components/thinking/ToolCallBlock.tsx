"use client";

import { Wrench, AlertCircle, CheckCircle, Timer, Loader2 } from "lucide-react";
import type { ToolCallEvent } from "@/types/message";
import Collapsible from "@/components/ui/Collapsible";

export default function ToolCallBlock({
  toolCall,
}: {
  readonly toolCall: ToolCallEvent;
}) {
  const statusIcon =
    toolCall.status === "running" ? (
      <Loader2 className="w-3 h-3 animate-spin text-accent" />
    ) : toolCall.status === "success" ? (
      <CheckCircle className="w-3 h-3 text-green-500" />
    ) : (
      <AlertCircle className="w-3 h-3 text-red-500" />
    );

  const header = (
    <>
      <Wrench className="w-3.5 h-3.5" color="#698394" />
      <span className="font-mono text-xs font-bold uppercase tracking-wider">
        {toolCall.name}
      </span>
      {statusIcon}
      {toolCall.durationMs !== undefined && (
        <span className="flex items-center gap-1 text-[10px] text-slate-400">
          <Timer className="w-3 h-3" />
          {toolCall.durationMs}ms
        </span>
      )}
    </>
  );

  return (
    <Collapsible
      header={header}
      defaultOpen={false}
      className="border border-slate-200 rounded-md bg-white overflow-hidden"
      headerClassName="flex items-center gap-2 p-2 hover:bg-slate-50 text-sm"
    >
      <div className="p-2 bg-slate-900 text-slate-300 font-mono text-[11px] space-y-2 border-t border-slate-200">
        <div>
          <span className="text-blue-400"># Arguments</span>
          <pre className="mt-1 whitespace-pre-wrap">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
        </div>
        {toolCall.result !== undefined && (
          <div className="border-t border-slate-700 pt-2">
            <span className="text-green-400"># Résultat</span>
            <pre className="mt-1 whitespace-pre-wrap max-h-40 overflow-y-auto">
              {typeof toolCall.result === "string"
                ? toolCall.result
                : JSON.stringify(toolCall.result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Collapsible>
  );
}
