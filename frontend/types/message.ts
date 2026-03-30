export type Role = "user" | "assistant" | "system" | "tool";

export type Citation = Readonly<{
  refId: number;
  text: string;
  chapter: number | null;
  page: number | null;
  url: string | null;
  domain: "book" | "web";
}>;

export type ThinkingSegment = Readonly<{

  id: string;

  type: "thinking";

  content: string;

}>;



export type ToolCallStatus = "running" | "success" | "error";



export type ToolCallEvent = Readonly<{

  id: string;

  type: "tool_call";

  name: string;

  arguments: Record<string, unknown>;

  status: ToolCallStatus;

  durationMs?: number;

  result?: unknown;

}>;



export type Step = ThinkingSegment | ToolCallEvent;



export type Message = Readonly<{

  id: string;

  role: Role;

  content: string;

  steps: readonly Step[];

  citations: readonly Citation[];

  createdAt: number;

}>;