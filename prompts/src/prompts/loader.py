import logging
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger("prompts.loader")

PromptNode = str | dict[str, "PromptNode"]


class PromptLoader:
    """Chargeur de prompts centralisé avec interpolation automatique des variables."""

    _registry: PromptNode = {}

    @classmethod
    def load(cls, path: str | Path = "prompts/prompts.yaml") -> None:
        """Charge le fichier YAML en mémoire.

        Le chemin est relatif au répertoire de travail. Dans un contexte Docker,
        il s'agit de la racine de l'application.
        """
        file_to_load = Path(path)

        if not file_to_load.exists():
            logger.error("Aucun fichier de prompts trouvé: %s", file_to_load)
            raise FileNotFoundError(f"prompts.yaml introuvable: {file_to_load}")

        with open(file_to_load, encoding="utf-8") as f:
            cls._registry = yaml.safe_load(f)
        logger.info("Prompts chargés depuis %s", file_to_load)

    @classmethod
    def get(cls, *keys: str, **variables: Any) -> str:
        """Récupère un prompt par son chemin et interpole les variables.

        Args:
            *keys: Chemin du prompt (ex: "system", "expert", "content").
            **variables: Variables optionnelles à formater dans le prompt.

        Returns:
            Le prompt formaté en chaîne de caractères.
        """
        node: object = cls._registry
        for k in keys:
            if isinstance(node, dict):
                try:
                    node = node[k]
                except KeyError:
                    raise KeyError(f"Clé introuvable : {k} (chemin: {'.'.join(keys)})")

        if not isinstance(node, str):
            raise TypeError(f"Le nœud ciblé n'est pas une chaîne : {type(node)}")

        variables.setdefault("date", date.today().isoformat())

        result = str(node)
        for k, v in variables.items():
            result = result.replace("{" + k + "}", str(v))

        return result
