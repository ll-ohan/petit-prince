import type { Message } from "./message";

export type ConversationMode = "persistent" | "ephemeral";

export type Conversation = Readonly<{
  id: string;
  title: string | null;
  createdAt: number;
  updatedAt: number;
  messages: readonly Message[];
  mode: ConversationMode;
}>;