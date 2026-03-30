"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useChat } from "@/hooks/useChat";
import { useUIStore } from "@/store/uiStore";
import MessageList from "@/components/chat/MessageList";
import InputBar from "@/components/chat/InputBar";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
import type { Message } from "@/types/message";

export default function EphemeralChatPage() {
  const [input, setInput] = useState("");
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { isGenerating, setGenerating, setMode } = useUIStore();
  const { sendMessage, streamingMessage } = useChat();

  useEffect(() => {
    setMode("ephemeral");
  }, [setMode]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages, streamingMessage]);

  const submitMessage = async () => {
    if (!input.trim() || isGenerating) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      steps: [],
      citations: [],
      createdAt: Date.now(),
    };

    setGenerating(true);
    setLocalMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const reply = await sendMessage(input, localMessages);
      if (reply) setLocalMessages((prev) => [...prev, reply]);
    } finally {
      setGenerating(false);
    }
  };

  const emptyState = (
    <div className="h-[60vh] flex flex-col items-center justify-center text-center px-6">
      <h1 className="text-3xl font-serif text-slate-800 mb-4">
        &ldquo;Nous sommes de ceux-là qui ne possèdent rien. Qui ne retiennent rien. Car on ne retient pas le vent.&rdquo;
      </h1>
      <p className="text-slate-500 max-w-md">
        Vous êtes en <strong>mode éphémère</strong>. Vos échanges ne seront pas
        enregistrés dans l&apos;historique de votre navigateur.
      </p>
    </div>
  );

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 flex flex-col relative min-w-0 overflow-x-hidden bg-sand">
        <Header mode="ephemeral" />

        <div ref={scrollRef} className="flex-1 overflow-y-auto bg-sand">
          <ErrorBoundary>
            <MessageList
              messages={localMessages}
              streamingMessage={streamingMessage}
              isGenerating={isGenerating}
              emptyState={emptyState}
            />
          </ErrorBoundary>
        </div>

        <InputBar
          value={input}
          onChange={setInput}
          onSubmit={() => { void submitMessage(); }}
          isGenerating={isGenerating}
          placeholder="Posez votre question secrète sur Le Petit Prince"
        />

        <Image
          src="/petit_prince_renard.png"
          alt="Le Petit Prince"
          width={400}
          height={600}
          className="pointer-events-none hidden md:block absolute bottom-6 right-6 w-auto h-[60vh] z-0"
        />
      </main>
    </div>
  );
}
