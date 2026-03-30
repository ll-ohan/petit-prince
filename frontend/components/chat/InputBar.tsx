"use client";

import { Send } from "lucide-react";
import { clsx } from "clsx";

type Props = Readonly<{
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isGenerating: boolean;
  placeholder?: string;
}>;

export default function InputBar({
  value,
  onChange,
  onSubmit,
  isGenerating,
  placeholder = "Posez votre question sur Le Petit Prince...",
}: Props) {
  return (
    <div className="p-6 bg-sand">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="max-w-2xl mx-auto relative group z-50"
      >
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder={placeholder}
          rows={1}
          disabled={isGenerating}
          className="w-full pl-6 pr-16 py-4 bg-white/30 border-assistant border rounded-2xl focus:ring-1 focus:ring-dark focus-visible:outline-none focus:bg-assistant transition-all resize-none shadow-inner disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={isGenerating || !value.trim()}
          className={clsx(
            "absolute right-3 bottom-3 p-2 rounded-xl transition-all -translate-y-1/7",
            value.trim() && !isGenerating
              ? "bg-warm text-sand shadow-md hover:scale-105"
              : "bg-sand text-user-bubble"
          )}
        >
          <Send size={20} />
        </button>
      </form>
      <p className="text-[10px] text-center text-slate-400 mt-3">
        Appuyez sur Entrée pour envoyer. Maj+Entrée pour une nouvelle ligne.
      </p>
    </div>
  );
}
