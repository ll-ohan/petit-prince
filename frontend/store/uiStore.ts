import { create } from "zustand";
import type { ConversationMode } from "@/types/conversation";

type UIState = {
  sidebarOpen: boolean;
  mode: ConversationMode;
  isGenerating: boolean;
  toggleSidebar: () => void;
  setMode: (mode: ConversationMode) => void;
  setGenerating: (status: boolean) => void;
};

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  mode: "persistent",
  isGenerating: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setMode: (mode) => set({ mode }),
  setGenerating: (isGenerating) => set({ isGenerating }),
}));