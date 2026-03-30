from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .. import settings
from ..schemas import WebSearchInput, WebSearchOutput, WebSearchResultItem


class WebSearchTool:
    """Outil de recherche web filtré via SearXNG."""

    async def execute(self, params: WebSearchInput) -> WebSearchOutput:
        """Exécute la recherche web sur les sites autorisés.

        Args:
            params: Les paramètres de recherche validés.

        Returns:
            Les snippets textuels des pages trouvées.
        """
        site_filter = ""
        if params.site != "all":
            site_filter = f"site:{params.site}"
        else:
            sites = " OR ".join([f"site:{d}" for d in settings.domains_list])
            site_filter = f"({sites})"

        full_query = f"{params.query} {site_filter}".strip()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.search_engine_url}/search",
                params={"q": full_query, "format": "json", "language": "fr"},
            )
            response.raise_for_status()
            data = response.json()

        results: list[WebSearchResultItem] = []
        ref_idx = 1

        for item in data.get("results", []):
            url = item.get("url", "")
            parsed = urlparse(str(url))
            domain: str = parsed.hostname or ""

            if domain and domain in settings.domains_list:
                raw_snippet = item.get("content", "")
                clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text(
                    separator=" ", strip=True
                )

                results.append(
                    WebSearchResultItem(
                        ref_id=ref_idx,
                        title=item.get("title", ""),
                        url=url,
                        snippet=clean_snippet,
                        source_domain=domain,
                    )
                )
                ref_idx += 1

                if len(results) >= params.max_results:
                    break

        return WebSearchOutput(results=results, query=params.query, total=len(results))
