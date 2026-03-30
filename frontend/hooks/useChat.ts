import { useState } from "react";
import { parseSSEStream } from "@/lib/streamParser";
import { chatCompletions, titrate } from "@/lib/api";
import { extractCitations } from "@/lib/citations";
import type { Message } from "@/types/message";
import type { ToolCallStartPayload } from "@/types/sse";
import { useUIStore } from "@/store/uiStore";

export function useChat() {
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(null);
  const { mode } = useUIStore();

  const sendMessage = async (
    content: string,
    history: readonly Message[],
    onTitleGenerated?: (title: string) => void
  ): Promise<Message | undefined> => {
    const isFirstExchange = history.filter((m) => m.role !== "system").length === 0;

    const response = await chatCompletions({
      messages: [...history, { role: "user", content }],
      stream: true,
    });

    if (!response.body) return;

    let currentMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      steps: [],
      citations: [],
      createdAt: Date.now(),
    };

    setStreamingMessage(currentMessage);

    let lastEventType: string | null = null;

    for await (const event of parseSSEStream(response.body)) {
      switch (event.event) {
        case "thinking":
          const lastStep = currentMessage.steps[currentMessage.steps.length - 1];
          const isContinuingThinking =
            lastEventType === "thinking" && lastStep?.type === "thinking";

          if (isContinuingThinking) {
            const updatedSteps = [...currentMessage.steps];
            updatedSteps[updatedSteps.length - 1] = {
              ...lastStep,
              content: lastStep.content + event.data.content,
            };
            currentMessage = { ...currentMessage, steps: updatedSteps };
          } else {
            currentMessage = {
              ...currentMessage,
              steps: [
                ...currentMessage.steps,
                {
                  id: crypto.randomUUID(),
                  type: "thinking",
                  content: event.data.content,
                },
              ],
            };
          }
          break;

        case "tool_call_start":
          const toolCallPayloads = event.data as ToolCallStartPayload[];
          let updatedSteps = [...currentMessage.steps];

          toolCallPayloads.forEach((payload) => {
            const existingStepIndex = updatedSteps.findIndex(
              (step) => step.type === "tool_call" && step.id === payload.id
            );

            if (existingStepIndex > -1) {
              const existingStep = updatedSteps[existingStepIndex];
              if (existingStep && existingStep.type === "tool_call") {
                let newArgs = existingStep.arguments;
                try {
                  const parsedArgs = JSON.parse(payload.function.arguments);
                  if (
                    typeof parsedArgs === "object" &&
                    parsedArgs !== null &&
                    !Array.isArray(parsedArgs)
                  ) {
                    newArgs = parsedArgs;
                  }
                } catch (e) {
                }
                updatedSteps[existingStepIndex] = {
                  ...existingStep,
                  arguments: newArgs,
                };
              }
            } else {
              let args = {};
              try {
                const parsedArgs = JSON.parse(payload.function.arguments);
                if (
                  typeof parsedArgs === "object" &&
                  parsedArgs !== null &&
                  !Array.isArray(parsedArgs)
                ) {
                  args = parsedArgs;
                }
              } catch (e) {
                // Ignore if JSON is incomplete
              }
              updatedSteps.push({
                id: payload.id,
                type: "tool_call" as const,
                name: payload.function.name,
                arguments: args,
                status: "running" as const,
              });
            }
          });

          currentMessage = {
            ...currentMessage,
            steps: updatedSteps,
          };
          break;

        case "tool_result":
          currentMessage = {
            ...currentMessage,
            steps: currentMessage.steps.map((step) => {
              if (step.type === "tool_call" && step.id === event.data.id) {
                try {
                  return {
                    ...step,
                    status: "success",
                    result: JSON.parse(event.data.result),
                  };
                } catch (e) {
                  return {
                    ...step,
                    status: "error",
                    result: "Invalid JSON output",
                  };
                }
              }
              return step;
            }),
          };
          break;

        case "text": {
          type TextChunk = { choices?: ReadonlyArray<{ delta?: { content?: string | null } }> };
          const chunk = event.data as TextChunk;
          const delta = chunk.choices?.[0]?.delta?.content ?? "";
          currentMessage = {
            ...currentMessage,
            content: currentMessage.content + delta,
          };
          break;
        }

        case "done":
          break;
      }
      lastEventType = event.event;
      setStreamingMessage({ ...currentMessage });
    }

    const { content: cleanContent, citations } = extractCitations(
      currentMessage.content
    );
    if (citations.length > 0) {
      currentMessage = { ...currentMessage, content: cleanContent, citations };
      setStreamingMessage({ ...currentMessage });
    }

    if (isFirstExchange && mode === "persistent" && currentMessage.content && onTitleGenerated) {
      void titrate({
        user_message: content,
        assistant_summary: currentMessage.content.substring(0, 150) + "...",
      }).then((data) => {
        if (data) onTitleGenerated(data.title);
      });
    }
    
    return currentMessage;
  };

  return { sendMessage, streamingMessage };
}