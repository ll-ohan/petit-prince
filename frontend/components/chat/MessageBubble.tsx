"use client";

import { memo, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import Image from "next/image";
import { Pencil, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import type { Message, Citation } from "@/types/message";
import ThinkingPanel from "../thinking/ThinkingPanel";
import CitationBlock from "./CitationBlock";

type Props = Readonly<{
  message: Message;
  isStreaming?: boolean;
  isLastMessage?: boolean;
  onCitationClick?: (citation: Citation) => void;
  onEdit?: (messageId: string, newContent: string) => void;
  onRetry?: () => void;
}>;

function MessageBubble({
  message,
  isStreaming = false,
  isLastMessage = false,
  onCitationClick,
  onEdit,
  onRetry,
}: Props) {
  const isAssistant = message.role === "assistant";
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);

  const handleSaveEdit = () => {
    if (onEdit && editText.trim()) onEdit(message.id, editText);
    setIsEditing(false);
  };

  // Mémoïzation de la transformation des références [N] → <sup>
  const contentWithCitations = useMemo(() => {
    if (!isAssistant) return message.content;
    return message.content.replace(
      /\[(\d+(?:,\s*\d+)*)\]/g,
      (_, numbersString: string) =>
        numbersString
          .split(",")
          .map((n) => n.trim())
          .map(
            (num) =>
              `<sup class="font-bold text-citation text-xs align-super mx-px"><a href="#citation-${num}" class="no-underline">[${num}]</a></sup>`
          )
          .join(" ")
    );
  }, [isAssistant, message.content]);

  return (
    <div
      className={clsx(
        "group flex w-full gap-4 p-6 transition-colors relative",
        isAssistant ? "justify-start" : "justify-end"
      )}
    >
      {isAssistant && (
        <div className="flex-shrink-0">
          <Image src="/chatbot.png" alt="Chatbot" width={55} height={55} className="rounded-full" />
        </div>
      )}

      <div
        className={clsx(
          "flex-1 min-w-0 space-y-2 max-w-2xl p-4 rounded-2xl z-40",
          isAssistant ? "bg-assistant" : "bg-user-bubble"
        )}
      >
        <div className="font-bold text-sm text-slate-900 flex items-center gap-2">
          <span>{isAssistant ? "Le Bibliothécaire" : "Vous"}</span>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {!isAssistant && onEdit && !isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="p-1 rounded-md hover:bg-slate-200 text-slate-500"
              >
                <Pencil size={14} />
              </button>
            )}
            {isAssistant && isLastMessage && onRetry && !isStreaming && (
              <button
                onClick={onRetry}
                className="p-1 rounded-md hover:bg-slate-200 text-slate-500"
              >
                <RefreshCw size={14} />
              </button>
            )}
          </div>
        </div>

        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full p-2 border rounded-md bg-white shadow-inner text-sm"
              rows={4}
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1 bg-amber-500 text-white rounded-md text-sm font-semibold hover:bg-amber-600"
              >
                Sauver &amp; Régénérer
              </button>
              <button
                onClick={() => {
                  setIsEditing(false);
                  setEditText(message.content);
                }}
                className="px-3 py-1 bg-slate-200 text-slate-700 rounded-md text-sm font-semibold hover:bg-slate-300"
              >
                Annuler
              </button>
            </div>
          </div>
        ) : (
          <>
            {isAssistant && message.steps.length > 0 && (
              <ThinkingPanel steps={message.steps} isLive={isStreaming} />
            )}

            <div className="prose prose-slate max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:text-slate-100">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                {contentWithCitations}
              </ReactMarkdown>
            </div>

            {isAssistant && message.citations.length > 0 && (
              <CitationBlock
                citations={message.citations}
                {...(onCitationClick && { onCitationClick })}
              />
            )}
          </>
        )}
      </div>

      {!isAssistant && (
        <div className="flex-shrink-0">
          <Image src="/user.png" alt="User" width={55} height={55} className="rounded-full" />
        </div>
      )}
    </div>
  );
}

export default memo(MessageBubble);
