import threading
from pathlib import Path

from sentence_transformers import SparseEncoder
from torch import Tensor

from .models import SparseVector

original_excepthook = threading.excepthook


def custom_thread_excepthook(args: threading.ExceptHookArgs) -> None:
    if args.thread is not None and args.thread.name == "Thread-auto_conversion":
        pass
    else:
        original_excepthook(args)


threading.excepthook = custom_thread_excepthook


class SpladeEncoder:
    """Encodeur sparse asymétrique basé sur SPLADE utilisant SparseEncoder.

    Attributes:
        model_name: Identifiant HuggingFace ou chemin local du modèle.
        device: 'cpu', 'cuda', ou 'mps'.
        threshold: Seuil en dessous duquel les poids sont ignorés.
    """

    def __init__(
        self,
        model_name: str = "naver/splade-v3",
        device: str = "cpu",
        threshold: float = 0.05,
        model_dir: str = ".models",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.threshold = threshold

        model_root = Path(model_dir)
        model_root.mkdir(parents=True, exist_ok=True)
        safe_name = model_name.replace("/", "_")
        local_path = model_root / safe_name

        if local_path.exists():
            model_source = str(local_path)
        else:
            model_source = model_name

        self.model = SparseEncoder(
            model_source, device=device, cache_folder=str(model_root)
        )

    def encode_batch(
        self, texts: list[str], batch_size: int = 32, is_query: bool = False
    ) -> list[SparseVector]:
        """Encode une liste de textes en mode batch efficace.

        Args:
            texts: Liste des textes à encoder.
            batch_size: Taille du batch pour l'inférence.
            is_query: Détermine s'il faut utiliser l'encodeur de requêtes.
        """
        if is_query:
            tensor = self.model.encode_query(texts, batch_size=batch_size)
        else:
            tensor = self.model.encode_document(texts, batch_size=batch_size)

        if isinstance(tensor, Tensor):
            t = tensor.coalesce() if getattr(tensor, "is_sparse", False) else tensor

            inds = None
            vals = None
            try:
                inds = t.indices()
                vals = t.values()
            except Exception:
                # Not a sparse tensor with indices/values; fallback to dense processing
                import numpy as _np

                arr = t.cpu().numpy()
                dense_results: list[SparseVector] = []
                for row in arr:
                    nz = _np.nonzero(row)[0].tolist()
                    nv = _np.asarray(row)[nz].astype(float).tolist()
                    dense_results.append(SparseVector(indices=nz, values=nv))
                return dense_results

            # inds shape for sparse COO: (ndim, nnz)
            if (
                inds is None  # pyright: ignore[reportUnnecessaryComparison]
                or vals is None  # pyright: ignore[reportUnnecessaryComparison]
            ):
                raise TypeError("Unable to extract indices/values from tensor")

            import numpy as _np

            inds_np = inds.cpu().numpy()
            vals_np = vals.cpu().numpy()

            # If inds has two rows (row, col) -> batched matrix
            if inds_np.ndim == 2 and inds_np.shape[0] >= 2:
                row_idx = inds_np[0].tolist()
                col_idx = inds_np[1].tolist()
                val_list = vals_np.tolist()

                # Group by row index
                from collections import defaultdict

                grouped_cols: dict[int, list[int]] = defaultdict(list)
                grouped_vals: dict[int, list[float]] = defaultdict(list)
                for r, c, v in zip(row_idx, col_idx, val_list):
                    grouped_cols[r].append(int(c))
                    grouped_vals[r].append(float(v))

                max_row = max(grouped_cols.keys()) if grouped_cols else -1
                results: list[SparseVector] = []
                for r in range(max_row + 1):
                    results.append(
                        SparseVector(
                            indices=grouped_cols.get(r, []),
                            values=grouped_vals.get(r, []),
                        )
                    )
                return results

            # Otherwise treat as single vector
            return [SparseVector.fromTensor(t)]
        else:
            raise TypeError(
                f"Expected a torch.Tensor from the model, but got {type(tensor)}"
            )

    def encode_document(self, text: str) -> list[SparseVector]:
        """Encode un document unique."""
        return self.encode_batch([text], is_query=False)

    def encode_query(self, text: str) -> list[SparseVector]:
        """Encode une requête unique."""
        return self.encode_batch([text], is_query=True)

    def tokenize(
        self,
        texts: str | list[str],
        padding: bool = True,
        truncation: bool = True,
        max_length: int = 512,
    ) -> Tensor:
        """Tokenise un texte ou une liste de textes.

        Utile pour inspecter comment le modèle découpe les mots ou pour
        préparer des inputs manuellement.

        Args:
            texts: Texte unique ou liste de textes.
            padding: Si True, ajoute du padding jusqu'à max_length.
            truncation: Si True, coupe les textes dépassant max_length.
            max_length: Longueur maximale de la séquence.
        """
        return self.model.tokenizer(  # type: ignore[no-any-return]
            texts,
            padding=padding,
            truncation=truncation,
            max_length=max_length,
            return_tensors="pt",
            return_offsets_mapping=True,
        ).to(self.device)
