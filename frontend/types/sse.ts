export type ToolCallStartPayload = Readonly<{
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string; // JSON string
  };
}>;

export type ToolResultPayload = Readonly<{
  id: string;
  result: string; // JSON string
}>;

export type SSEEvent =
  | { readonly event: "thinking"; readonly data: { content: string } }
  | { readonly event: "tool_call_start"; readonly data: readonly ToolCallStartPayload[] }
  | { readonly event: "tool_result"; readonly data: ToolResultPayload }
  | { readonly event: "text"; readonly data: unknown } // Structure OpenAI-like à parser dynamiquement
  | { readonly event: "done"; readonly data: "[DONE]" };