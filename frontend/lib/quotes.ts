export const QUOTES = [
  "On ne voit bien qu'avec le cœur. L'essentiel est invisible pour les yeux.",
  "Fais de ta vie un rêve, et d'un rêve, une réalité.",
  "On est seul aussi chez les hommes.",
  "Elles se croient importantes comme des baobabs.",
  "Un jour, j'ai vu le soleil se coucher quarante-trois fois !",
  "On court le risque de pleurer un peu, si l'on s'est laissé apprivoiser.",
  "Dessine-moi un mouton !",
  "Elle n'a que quatre épines pour se protéger contre le monde.",
  "C'est le temps que tu as perdu pour ta rose qui fait ta rose si importante.",
  "Ma rose est éphémère.",
] as const;

const INDEX_KEY = "petit_prince_quote_index";

/**
 * Retourne la citation courante et avance l'index dans localStorage.
 * Protégé contre le double-mount de React StrictMode via sessionStorage.
 */
export function getNextQuote(convId?: string): string {
  const TTL_MS = 1500;
  const fallback = QUOTES[0];

  try {
    const raw = localStorage.getItem(INDEX_KEY);
    const current = raw ? parseInt(raw, 10) : 0;
    const idx = isNaN(current) ? 0 : current % QUOTES.length;

    const tsKey = `petit_prince_quote_ts_${convId ?? "global"}`;
    const rawTs = sessionStorage.getItem(tsKey);
    const now = Date.now();

    if (rawTs && now - (parseInt(rawTs, 10) || 0) < TTL_MS) {
      return QUOTES[idx] ?? fallback;
    }

    const next = (idx + 1) % QUOTES.length;
    localStorage.setItem(INDEX_KEY, String(next));
    sessionStorage.setItem(tsKey, String(now));

    return QUOTES[idx] ?? fallback;
  } catch {
    return fallback;
  }
}
