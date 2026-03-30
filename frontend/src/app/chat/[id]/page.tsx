"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { useChat } from "@/hooks/useChat";
import { useConversationStore } from "@/hooks/useConversations";
import { useUIStore } from "@/store/uiStore";
import MessageList from "@/components/chat/MessageList";
import InputBar from "@/components/chat/InputBar";
import CitationModal from "@/components/chat/CitationModal";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
import { getNextQuote } from "@/lib/quotes";
import type { Citation, Message } from "@/types/message";

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [rotatingQuote, setRotatingQuote] = useState<string | null>(null);

  const { mode, isGenerating, setGenerating } = useUIStore();
  const { conversations, addMessage, updateTitle, editMessageAndTruncate, removeLastMessage } =
    useConversationStore();
  const { sendMessage, streamingMessage } = useChat();

  useEffect(() => {
    if (mode === "ephemeral") router.replace("/chat");
  }, [mode, router]);

  useEffect(() => {
    if (!id) return;
    setRotatingQuote(getNextQuote(id));
  }, [id]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversations, streamingMessage]);

  const conversation = conversations.find((c) => c.id === id);
  const messages = conversation?.messages ?? [];

  const handleEdit = async (messageId: string, newContent: string) => {
    if (!id || isGenerating) return;
    setGenerating(true);
    try {
      await editMessageAndTruncate(id, messageId, newContent);
      const history =
        useConversationStore.getState().conversations.find((c) => c.id === id)?.messages ?? [];
      const lastMessage = history[history.length - 1];
      if (lastMessage?.role === "user") {
        const reply = await sendMessage(lastMessage.content, history.slice(0, -1));
        if (reply) await addMessage(id, reply);
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleRetry = async () => {
    if (!id || isGenerating || messages.length === 0) return;
    if (messages[messages.length - 1]?.role !== "assistant") return;
    setGenerating(true);
    try {
      await removeLastMessage(id);
      const history =
        useConversationStore.getState().conversations.find((c) => c.id === id)?.messages ?? [];
      const userPrompt = history[history.length - 1];
      if (userPrompt?.role === "user") {
        const reply = await sendMessage(userPrompt.content, history.slice(0, -1));
        if (reply) await addMessage(id, reply);
      }
    } finally {
      setGenerating(false);
    }
  };

  const submitMessage = async () => {
    if (!input.trim() || isGenerating) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user" as const,
      content: input,
      steps: [],
      citations: [],
      createdAt: Date.now(),
    };

    setGenerating(true);
    setInput("");
    await addMessage(id, userMessage);

    try {
      const reply = await sendMessage(input, messages, (title) => {
        updateTitle(id, title);
      });
      if (reply) await addMessage(id, reply);
    } finally {
      setGenerating(false);
    }
  };

  const emptyState = (
    <div className="h-[60vh] flex flex-col items-center justify-center text-center px-6">
      <h1 className="text-4xl font-serif text-warm mb-4 z-40">
        &ldquo;{rotatingQuote ?? "On ne voit bien qu'avec le cœur. L'essentiel est invisible pour les yeux."}&rdquo;
      </h1>
      <p className="text-dark max-w-xl mt-10 z-40">
        Posez n&apos;importe quelle question sur l&apos;œuvre de Saint-Exupéry.
        Je chercherai pour vous les passages exacts et les analyses d&apos;experts.
      </p>
    </div>
  );

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 flex flex-col relative min-w-0 overflow-x-hidden bg-sand">
        <Header mode="persistent" title={conversation?.title ?? null} />

        <div ref={scrollRef} className="flex-1 overflow-y-auto bg-sand">
          <ErrorBoundary>
            <MessageList
              messages={messages}
              streamingMessage={streamingMessage}
              isGenerating={isGenerating}
              onCitationClick={setSelectedCitation}
              onEdit={(messageId, newContent) => { void handleEdit(messageId, newContent); }}
              onRetry={() => { void handleRetry(); }}
              emptyState={emptyState}
            />
          </ErrorBoundary>
        </div>

        <InputBar
          value={input}
          onChange={setInput}
          onSubmit={() => { void submitMessage(); }}
          isGenerating={isGenerating}
        />

        <Image
          src="/petit_prince.png"
          alt="Le Petit Prince"
          width={400}
          height={600}
          className="pointer-events-none hidden md:block absolute bottom-6 right-6 w-auto h-[60vh] z-0"
        />

        {selectedCitation && (
          <CitationModal citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
        )}
      </main>
    </div>
  );
}
