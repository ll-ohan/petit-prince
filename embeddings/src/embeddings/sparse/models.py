from pydantic import BaseModel
from torch import Tensor, sparse_coo


class SparseVector(BaseModel):
    """Représentation d'un vecteur sparse Pydantic.

    Fournit un utilitaire `fromTensor` pour construire l'objet à partir
    d'un `torch.Tensor` (COO sparse).
    """

    indices: list[int]
    values: list[float]

    @classmethod
    def fromTensor(cls, tensor: Tensor) -> "SparseVector":
        """Construit un `SparseVector` à partir d'un tenseur PyTorch.

        Supporte :
        - tenseur sparse COO (`tensor.is_sparse and tensor.layout == torch.sparse_coo`)

        Args:
            tensor: un `torch.Tensor` (sparse ou dense)

        Returns:
            SparseVector: instance avec `indices` et `values` lists.
        """

        if tensor.is_sparse and tensor.layout == sparse_coo:
            t = tensor.coalesce()
            # Pour un vecteur unique, les indices sont en t.indices()[0]
            inds = t.indices()
            vals = t.values()

            if inds.ndim == 2 and inds.size(0) >= 1:
                token_idx = inds[0].cpu().numpy().tolist()
            else:
                token_idx = inds.cpu().numpy().ravel().tolist()

            token_vals = vals.cpu().numpy().tolist()

            return cls(indices=token_idx, values=token_vals)

        raise ValueError(
            "fromTensor expects a sparse COO tensor representing a single vector"
        )
