"use client";

import { X } from "lucide-react";
import type { Citation } from "@/types/message";

type Props = {
  citation: Citation;
  onClose: () => void;
};

export default function CitationModal({ citation, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b flex items-center">
          <h3 className="font-bold text-slate-800">Source: Chapitre {citation.chapter}, p.{citation.page}</h3>
          <button onClick={onClose} className="ml-auto p-1 rounded-full hover:bg-slate-100">
            <X size={20} />
          </button>
        </div>
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <p className="text-slate-600 leading-relaxed whitespace-pre-wrap">
            {citation.text}
          </p>
        </div>
      </div>
    </div>
  );
}
