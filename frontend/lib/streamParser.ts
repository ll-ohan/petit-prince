import type { SSEEvent, ToolCallStartPayload, ToolResultPayload } from "@/types/sse";

export async function* parseSSEStream(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent, void, unknown> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      
      // Les événements SSE sont séparés par des doubles sauts de ligne
      const events = buffer.split("\n\n");
      // On garde le dernier fragment incomplet dans le buffer
      buffer = events.pop() ?? "";

      for (const eventStr of events) {
        if (!eventStr.trim()) continue;

        const lines = eventStr.split("\n");
        let eventType = "message"; // default SSE type
        let dataStr = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.substring(7).trim();
          } else if (line.startsWith("data: ")) {
            dataStr = line.substring(6).trim();
          }
        }

        if (!dataStr) continue;

        if (dataStr === "[DONE]") {
          yield { event: "done", data: "[DONE]" };
          return;
        }

        try {
          const parsedData = JSON.parse(dataStr) as unknown;
          
          switch (eventType) {
            case "thinking":
              yield { event: "thinking", data: parsedData as { content: string } };
              break;
            case "tool_call_start":
              yield { event: "tool_call_start", data: parsedData as readonly ToolCallStartPayload[] };
              break;
            case "tool_result":
              yield { event: "tool_result", data: parsedData as ToolResultPayload };
              break;
            case "text":
              yield { event: "text", data: parsedData };
              break;
            default:
              console.warn(`Unrecognized SSE event type: ${eventType}`);
          }
        } catch (e) {
          console.error("Failed to parse SSE data chunk JSON", e, dataStr);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}