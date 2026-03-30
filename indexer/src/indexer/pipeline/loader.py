import re
from dataclasses import dataclass


@dataclass(slots=True)
class RawPage:
    """Représentation brute d'une page extraite du texte."""

    text: str
    page_number: int
    chapter_id: int


def load_source(file_path: str) -> list[RawPage]:
    """Charge et parse le fichier texte source en pages brutes.

    Détecte les séparateurs de pages '---' et les balises 'CHAPITRE X'.

    Args:
        file_path: Le chemin vers le fichier texte.

    Returns:
        Une liste d'objets RawPage contenant le texte, la page et le chapitre.
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    raw_pages = re.split(r"\n---\n", content)

    pages: list[RawPage] = []
    current_chapter = 0

    for i, page_text in enumerate(raw_pages, start=1):
        clean_text = page_text.strip()
        if not clean_text:
            continue

        # Détection du chapitre (ex: "CHAPITRE 1")
        chapter_match = re.search(r"^CHAPITRE\s+(\d+)", clean_text, re.MULTILINE)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            clean_text = re.sub(
                r"^CHAPITRE\s+\d+\s*", "", clean_text, flags=re.MULTILINE
            ).strip()

        if clean_text:
            pages.append(
                RawPage(text=clean_text, page_number=i, chapter_id=current_chapter)
            )

    return pages
