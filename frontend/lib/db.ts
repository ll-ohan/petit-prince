import { openDB, type IDBPDatabase } from "idb";
import type { Conversation } from "@/types/conversation";

const DB_NAME = "petit_prince_db";
const STORE_NAME = "conversations";

export async function initDB(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("updatedAt", "updatedAt");
      }
    },
  });
}

export async function saveConversation(conv: Conversation): Promise<void> {
  const db = await initDB();
  await db.put(STORE_NAME, conv);
}

export async function getAllConversations(): Promise<Conversation[]> {
  const db = await initDB();
  const convs = await db.getAllFromIndex(STORE_NAME, "updatedAt");
  return convs.reverse(); // Plus récent en premier
}

export async function deleteConversation(id: string): Promise<void> {
  const db = await initDB();
  await db.delete(STORE_NAME, id);
}