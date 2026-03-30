"use client";

import type { Message, Citation } from "@/types/message";
import MessageBubble from "./MessageBubble";

type Props = Readonly<{
  messages: readonly Message[];
  streamingMessage: Message | null;
  isGenerating: boolean;
  onCitationClick?: (citation: Citation) => void;
  onEdit?: (messageId: string, newContent: string) => void;
  onRetry?: () => void;
  /** Nœud affiché quand la liste est vide et qu'il n'y a pas de stream en cours */
  emptyState?: React.ReactNode;
}>;

export default function MessageList({
  messages,
  streamingMessage,
  isGenerating,
  onCitationClick,
  onEdit,
  onRetry,
  emptyState,
}: Props) {
  const isEmpty = messages.length === 0 && !streamingMessage;

  return (
    <div className="max-w-5xl mx-auto px-4">
      {messages.map((msg, index) => {
        // Évite le doublon quand le message streamé est ajouté à l'historique
        if (streamingMessage?.id === msg.id) return null;
        return (
          <MessageBubble
            key={msg.id}
            message={msg}
            isStreaming={false}
            isLastMessage={index === messages.length - 1}
            {...(onCitationClick && { onCitationClick })}
            {...(onEdit && { onEdit })}
            {...(onRetry && { onRetry })}
          />
        );
      })}

      {streamingMessage && (
        <MessageBubble
          message={streamingMessage}
          isStreaming={isGenerating}
          {...(onCitationClick && { onCitationClick })}
        />
      )}

      {isEmpty && emptyState}
    </div>
  );
}
