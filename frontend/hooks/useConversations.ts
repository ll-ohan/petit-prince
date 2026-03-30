import { create } from "zustand";
import {
  saveConversation,
  getAllConversations,
  deleteConversation as dbDelete,
} from "@/lib/db";
import type { Conversation } from "@/types/conversation";
import type { Message } from "@/types/message";

type ConversationStore = {
  conversations: Conversation[];
  activeId: string | null;
  loadAll: () => Promise<void>;
  addMessage: (id: string, message: Message) => Promise<void>;
  updateTitle: (id: string, title: string) => Promise<void>;
  setActive: (id: string | null) => void;
  remove: (id: string) => Promise<void>;
  editMessageAndTruncate: (
    id: string,
    messageId: string,
    newContent: string
  ) => Promise<void>;
  removeLastMessage: (id: string) => Promise<void>;
};

export const useConversationStore = create<ConversationStore>((set, get) => ({
  conversations: [],
  activeId: null,

  loadAll: async () => {
    const data = await getAllConversations();
    set({ conversations: data });
  },

  setActive: (id) => set({ activeId: id }),

  addMessage: async (id, message) => {
    const { conversations } = get();
    const existing = conversations.find((c) => c.id === id);

    if (existing) {
      const updated: Conversation = {
        ...existing,
        messages: [...existing.messages, message],
        updatedAt: Date.now(),
      };
      await saveConversation(updated);
      set({
        conversations: conversations.map((c) => (c.id === id ? updated : c)),
      });
    } else {
      const newConversation: Conversation = {
        id,
        title: "Nouvelle conversation",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [message],
        mode: "persistent",
      };
      await saveConversation(newConversation);
      set({ conversations: [newConversation, ...conversations] });
    }
  },

  updateTitle: async (id, title) => {
    const { conversations } = get();
    const existing = conversations.find((c) => c.id === id);

    if (existing) {
      const updated: Conversation = {
        ...existing,
        title,
        updatedAt: Date.now(),
      };

      await saveConversation(updated);

      set({
        conversations: conversations
          .map((c) => (c.id === id ? updated : c))
          .sort((a, b) => b.updatedAt - a.updatedAt),
      });
    }
  },

  remove: async (id) => {
    await dbDelete(id);
    set({ conversations: get().conversations.filter((c) => c.id !== id) });
  },

  editMessageAndTruncate: async (id, messageId, newContent) => {
    const { conversations } = get();
    const conv = conversations.find((c) => c.id === id);
    if (!conv) return;

    const msgIndex = conv.messages.findIndex((m) => m.id === messageId);
    if (msgIndex === -1) return;

    // Create a new messages array, truncated and with the edited message
    const updatedMessages = conv.messages.slice(0, msgIndex);
    const editedMessage = { ...conv.messages[msgIndex], content: newContent };
    updatedMessages.push(editedMessage as Message);

    const updatedConv: Conversation = {
      ...conv,
      messages: updatedMessages,
      updatedAt: Date.now(),
    };

    await saveConversation(updatedConv);
    set({
      conversations: conversations.map((c) => (c.id === id ? updatedConv : c)),
    });
  },

  removeLastMessage: async (id: string) => {
    const { conversations } = get();
    const conv = conversations.find((c) => c.id === id);
    if (conv && conv.messages.length > 0) {
      const updated: Conversation = {
        ...conv,
        messages: conv.messages.slice(0, -1),
        updatedAt: Date.now(),
      };
      await saveConversation(updated);
      set({
        conversations: conversations.map((c) => (c.id === id ? updated : c)),
      });
    }
  },
}));