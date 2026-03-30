"use client";

import { BookOpen, Globe, ExternalLink } from "lucide-react";
import type { Citation } from "@/types/message";

type Props = Readonly<{
  citations: readonly Citation[];
  onCitationClick?: (citation: Citation) => void;
}>;

export default function CitationBlock({ citations, onCitationClick }: Props) {
  return (
    <div className="mt-6 pt-4 border-t border-slate-200">
      <h4 className="text-xs font-semibold text-[#E8D7CA] uppercase tracking-wider mb-3">
        Sources
      </h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {citations.map((citation) => (
          <div
            id={`citation-${citation.refId}`}
            key={citation.refId}
            onClick={() => onCitationClick?.(citation)}
            className="flex items-start gap-3 p-2 rounded-lg border border-[#494949]  hover:border-[#E8D7CA] transition-colors group cursor-pointer"
          >
            <div className="flex-shrink-0 mt-1">
              {citation.domain === "book" ? (
                <BookOpen size={14} className="text-[#E8D7CA]" />
              ) : (
                <Globe size={14} className="text-blue-500" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold bg-[#E8D7CA] text-white px-1.5 py-0.5 rounded">
                  {citation.refId}
                </span>
                <span className="text-xs font-medium text-slate-700 truncate">
                  {citation.domain === "book"
                    ? `Chapitre ${citation.chapter}, p.${citation.page}`
                    : citation.url?.replace(/^https?:\/\//, "")}
                </span>
              </div>

              <p className="text-[11px] text-[#E8D7CA] line-clamp-1 mt-0.5 italic">
                "{citation.text}"
              </p>
            </div>

            {citation.url && (
              <a
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-slate-100 rounded"
              >
                <ExternalLink size={12} className="text-slate-400" />
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}