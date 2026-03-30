"use client";

import { Ghost, Plus } from "lucide-react";

type PersistentProps = Readonly<{
  mode: "persistent";
  title?: string | null;
}>;

type EphemeralProps = Readonly<{
  mode: "ephemeral";
}>;

type Props = PersistentProps | EphemeralProps;

export default function Header(props: Props) {
  return (
    <header className="h-14 flex items-center px-6 bg-sand backdrop-blur-md sticky top-0 z-10">
      {props.mode === "ephemeral" ? (
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-accent">
          <Ghost size={14} /> Mode Éphémère
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          {props.title ? (
            <h1 className="text-base truncate">{props.title}</h1>
          ) : (
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-slate-400">
              <Plus size={14} /> Nouvelle Conversation
            </div>
          )}
        </div>
      )}
    </header>
  );
}
