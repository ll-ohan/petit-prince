const BASE_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "";

type ChatCompletionsRequest = {
  messages: ReadonlyArray<{ role: string; content: string }>;
  stream?: boolean;
  model?: string;
};

type TitrateRequest = {
  user_message: string;
  assistant_summary: string;
};

type TitrateResponse = {
  title: string;
};

export async function chatCompletions(
  body: ChatCompletionsRequest
): Promise<Response> {
  return fetch(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function titrate(
  body: TitrateRequest
): Promise<TitrateResponse | null> {
  try {
    const res = await fetch(`${BASE_URL}/titrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as TitrateResponse;
  } catch {
    return null;
  }
}
