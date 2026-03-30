from typing import Any

from embeddings.sparse import SpladeEncoder

from ..models import Chunk

from .loader import RawPage

_APOSTROPHES = ("'", "\u2019")

_PageRange = tuple[int, int, int]


class TextChunker:
    """Découpe le texte en respectant les limites de tokens via SpladeEncoder.

    Attributes:
        encoder: Instance de SpladeEncoder contenant le tokenizer.
        chunk_size: La taille maximale d'un chunk en tokens (défaut: 300).
        overlap: Le nombre de tokens chevauchant entre deux chunks (défaut: 50).
    """

    def __init__(
        self, encoder: SpladeEncoder, chunk_size: int = 300, overlap: int = 50
    ) -> None:
        self.encoder = encoder
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_pages(self, pages: list[RawPage]) -> list[Chunk]:
        """Transforme une liste de pages brutes en chunks standardisés."""
        chunks: list[Chunk] = []
        global_chunk_idx = 0

        for chapter_id, chapter_pages in self._group_by_chapter(pages).items():
            full_text, page_ranges = self._build_chapter_text(chapter_pages)
            token_ids, offsets = self._tokenize_chapter(full_text)

            start = 0
            while start < len(token_ids):
                end = min(start + self.chunk_size, len(token_ids))
                chunk_text = self._extract_chunk_text(
                    full_text, token_ids, offsets, start, end
                )

                if chunk_text:
                    page_start, page_end = self._page_range_for_text(
                        chunk_text,
                        full_text,
                        offsets,
                        start,
                        end,
                        page_ranges,
                        chapter_pages[0].page_number,
                        chapter_pages[-1].page_number,
                    )
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            chapter_id=chapter_id,
                            page_start=page_start,
                            page_end=page_end,
                            chunk_index=global_chunk_idx,
                        )
                    )
                    global_chunk_idx += 1

                start += self.chunk_size - self.overlap

        return chunks

    @staticmethod
    def _group_by_chapter(pages: list[RawPage]) -> dict[int, list[RawPage]]:
        chapters: dict[int, list[RawPage]] = {}
        for p in pages:
            chapters.setdefault(p.chapter_id, []).append(p)
        return chapters

    @staticmethod
    def _build_chapter_text(pages: list[RawPage]) -> tuple[str, list[_PageRange]]:
        """Concatène les pages d'un chapitre et retourne les plages de caractères par page."""
        parts: list[str] = []
        page_ranges: list[_PageRange] = []
        cursor = 0

        for p in pages:
            if parts:
                parts.append(" ")
                cursor += 1
            start = cursor
            parts.append(p.text)
            cursor += len(p.text)
            page_ranges.append((p.page_number, start, cursor))

        return "".join(parts), page_ranges

    def _tokenize_chapter(self, text: str) -> tuple[list[int], Any]:
        encoded: Any = self.encoder.tokenize(text, padding=False, truncation=False)
        token_ids = list(encoded["input_ids"][0].cpu().numpy())  # pyright: ignore

        offsets: Any = None
        if "offset_mapping" in encoded:
            try:
                offsets = encoded["offset_mapping"][0].cpu().numpy()  # pyright: ignore
            except Exception:
                offsets = None

        return token_ids, offsets

    def _extract_chunk_text(
        self,
        full_text: str,
        token_ids: list[int],
        offsets: Any,
        start: int,
        end: int,
    ) -> str:
        if offsets is not None:
            char_start, char_end = self._char_bounds_from_offsets(offsets, start, end)
            if (
                char_start is not None
                and char_end is not None
                and char_end > char_start
            ):
                char_start, char_end = self._fix_apostrophe_boundaries(
                    full_text, char_start, char_end
                )
                if char_end > char_start:
                    return full_text[char_start:char_end].strip()

        return str(
            self.encoder.model.tokenizer.decode(
                token_ids[start:end], skip_special_tokens=True
            )
        ).strip()

    @staticmethod
    def _char_bounds_from_offsets(
        offsets: Any, start: int, end: int
    ) -> tuple[int | None, int | None]:
        """Trouve les bornes de caractères correspondant à la fenêtre [start, end)."""
        char_start: int | None = None
        for i in range(start, end):
            s, e = int(offsets[i][0]), int(offsets[i][1])  # pyright: ignore
            if e > s:
                char_start = s
                break

        char_end: int | None = None
        for j in range(end - 1, start - 1, -1):
            s, e = int(offsets[j][0]), int(offsets[j][1])  # pyright: ignore
            if e > s:
                char_end = e
                break

        return char_start, char_end

    @staticmethod
    def _fix_apostrophe_boundaries(
        text: str, char_start: int, char_end: int
    ) -> tuple[int, int]:
        """Recule/avance les bornes pour ne pas couper sur une apostrophe."""
        apos = _APOSTROPHES

        if char_start > 0 and text[char_start - 1] in apos:
            prev = text.rfind(" ", 0, char_start - 1)
            char_start = prev + 1 if prev != -1 else 0

        if char_start < len(text) and text[char_start] in apos:
            prev = text.rfind(" ", 0, char_start)
            char_start = prev + 1 if prev != -1 else 0

        if char_end < len(text) and text[char_end] in apos:
            nxt = text.find(" ", char_end + 1)
            char_end = nxt if nxt != -1 else len(text)

        if char_end > 0 and text[char_end - 1] in apos:
            nxt = text.find(" ", char_end)
            char_end = nxt if nxt != -1 else len(text)

        return char_start, char_end

    def _page_range_for_text(
        self,
        chunk_text: str,
        full_text: str,
        offsets: Any,
        start: int,
        end: int,
        page_ranges: list[_PageRange],
        default_start: int,
        default_end: int,
    ) -> tuple[int, int]:
        """Détermine les numéros de pages couverts par un chunk."""
        cs: int | None = None
        ce: int | None = None

        if offsets is not None:
            cs, ce = self._char_bounds_from_offsets(offsets, start, end)
        else:
            found = full_text.find(chunk_text)
            if found != -1:
                cs, ce = found, found + len(chunk_text)

        if cs is not None and ce is not None:
            covered = [pn for pn, s, e in page_ranges if not (e <= cs or s >= ce)]
            if covered:
                return min(covered), max(covered)

        return default_start, default_end
