from embeddings.sparse import SpladeEncoder

from qdrant_manager import retrieve

from ..schemas import RetrieverInput, RetrieverOutput, RetrieverResultItem


class RetrieverTool:
    """Outil de recherche sémantique dans le livre Le Petit Prince.

    Maintient une instance du modèle SPLADE en mémoire pour encoder
    les requêtes à la volée de manière performante.
    """

    def __init__(self, encoder: SpladeEncoder) -> None:
        self.encoder = encoder

    async def execute(self, params: RetrieverInput) -> RetrieverOutput:
        """Exécute la recherche dans Qdrant avec filtrage par payload.

        Args:
            params: Les paramètres validés de la requête.

        Returns:
            Les résultats formatés pour le LLM.
        """
        # encode_query returns a list of SparseVector (one per input); use the first vector
        encoded = self.encoder.encode_query(params.query)
        if not encoded:
            raise ValueError("Encoder returned no vectors for query")
        query_vector = encoded[0]

        raw_results = retrieve.search_passages(
            query_vector=query_vector,
            top_k=params.top_k,
            chapter_filter=params.chapter_filter,
        )

        formatted_results: list[RetrieverResultItem] = []
        for r in raw_results:
            if isinstance(r, RetrieverResultItem):
                formatted_results.append(r)
            else:
                formatted_results.append(RetrieverResultItem(**r))

        return RetrieverOutput(
            results=formatted_results, query=params.query, total=len(formatted_results)
        )
