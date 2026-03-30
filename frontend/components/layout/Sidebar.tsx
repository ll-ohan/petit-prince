"use client";

import { useEffect } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  History,
  Ghost,
  ChevronLeft,
} from "lucide-react";
import Image from "next/image";
import { useConversationStore } from "@/hooks/useConversations";
import { useUIStore } from "@/store/uiStore";
import { useRouter, useParams } from "next/navigation";
import { clsx } from "clsx";

export default function Sidebar() {
  const { conversations, loadAll, remove } = useConversationStore();
  const { sidebarOpen, toggleSidebar, mode, setMode } = useUIStore();
  const router = useRouter();
  const params = useParams();

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const createNewChat = () => {
    const id = crypto.randomUUID();
    router.push(`/chat/${id}`);
  };

  const switchToPersistent = () => {
    setMode("persistent");
    createNewChat();
  };

  if (!sidebarOpen) {
    return (
      <button
        onClick={toggleSidebar}
        className="fixed bottom-4 left-4 p-2 bg-white border border-slate-200 rounded-full shadow-lg z-50 hover:bg-slate-50"
      >
        <MessageSquare size={20} className="text-slate-600" />
      </button>
    );
  }

  return (
    <aside
      className="w-72 h-screen bg-[#B0A190]/50 flex flex-col z-40 relative"
    >
      <div className="p-4 flex items-center justify-between">
        <h2 className="font-bold text-[#494949] flex items-center gap-2">
          <History size={18}/> Historique
        </h2>
        <button
          onClick={toggleSidebar}
          className="p-1 hover:bg-[#698394]-200 rounded text-[#698394]"
        >
          <ChevronLeft size={18} />
        </button>
      </div>

      <div className="px-4 mb-4">
        <button
          onClick={createNewChat}
          className="w-full py-2.5 px-4 bg-[#698394] hover:bg-[#698394]-400 text-white rounded-xl font-medium flex items-center justify-center gap-2 transition-all shadow-sm"
        >
          <Plus size={18} /> Nouveau chat
        </button>
      </div>

      {/* Switcher de Mode */}
      <div className="px-4 mb-6">
        <div className="flex p-1 bg-[#494949] rounded-lg">
          <button
            onClick={switchToPersistent}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 py-1.5 text-xs font-semibold rounded-md transition-all",
              mode === "persistent"
                ? "bg-white text-[#494949] shadow-sm"
                : "text-white hover:text-[#698394]-700"
            )}
          >
            <MessageSquare size={14} /> Persistant
          </button>
          <button
            onClick={() => {
              setMode("ephemeral");
              router.push("/chat");
            }}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 py-1.5 text-xs font-semibold rounded-md transition-all",
              mode === "ephemeral"
                ? "bg-white text-[#494949] shadow-sm"
                : "text-white hover:text-[#698394]-700"
            )}
          >
            <Ghost size={14} /> Éphémère
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={clsx(
              "group flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors inset-shadow-md",
              params.id === conv.id
                ? "bg-[#494949]/10 text-[#494949]"
                : "hover:bg-[#494949]/20 text-[#698394]/95"
            )}
            onClick={() => {
              setMode("persistent");
              router.push(`/chat/${conv.id}`);
            }}
          >
            <MessageSquare size={16} className="shrink-0" />
            <span className="text-sm truncate flex-1">
              {conv.title || "Nouvelle conversation"}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                remove(conv.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-[#698394] rounded text-[#698394] hover:text-red-500 transition-all"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <Image
          src="/small_petit_prince.png"
          alt="Le Petit Prince"
          width={288}
          height={288}
          className="pointer-events-none hidden md:block absolute bottom-0 right-0 w-full z-0"
        />
    </aside>
  );
}