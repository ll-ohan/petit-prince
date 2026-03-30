import type { Citation } from "@/types/message";

const SOURCE_REGEX = /<sources>([\s\S]*)<\/sources>/;

/**
 * Extrait le bloc <sources>...</sources> du contenu d'un message assistant,
 * parse les citations JSON et retourne le contenu nettoyé + les citations.
 */
export function extractCitations(rawContent: string): {
  content: string;
  citations: readonly Citation[];
} {
  const match = rawContent.match(SOURCE_REGEX);
  if (!match?.[1]) {
    return { content: rawContent, citations: [] };
  }

  try {
    const citations = JSON.parse(match[1]) as Citation[];
    const content = rawContent.replace(SOURCE_REGEX, "").trim();
    return { content, citations };
  } catch {
    console.error("[citations] Failed to parse <sources> block");
    return { content: rawContent, citations: [] };
  }
}