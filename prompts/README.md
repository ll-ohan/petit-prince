# prompts — Registre centralisé des prompts

Module de gestion des prompts système. Tous les textes injectés dans le LLM (system prompt, prompts de titrage, descriptions des tools) sont définis dans un seul fichier YAML versionné, puis chargés au démarrage des services qui en ont besoin.

---

## Pourquoi centraliser les prompts ?

Éparpiller les prompts dans le code présente plusieurs risques : modifications silencieuses, duplications, difficultés de relecture. Ce module impose un point d'entrée unique, ce qui facilite :
- **La maintenance** : modifier un prompt sans toucher au code Python
- **Le versioning** : l'historique Git du fichier YAML retrace l'évolution des prompts
- **La réutilisation** : un même prompt peut être partagé entre plusieurs modules

---

## Fichier `prompts.yaml`

Le fichier est structuré en trois sections principales :

```yaml
version: "1.0.0"

system:
  expert:
    content: |
      Tu es un expert passionné de l'œuvre "{book_title}"...

developer:
  titler:
    content: |
      Tu es un assistant qui génère des titres courts...
  title_user_template: |
    Voici le premier échange...

tool:
  retriever:
    description: |
      Recherche des extraits pertinents du livre...
  web_search:
    description: |
      Effectue une recherche sur les sites autorisés...
```

### Section `system`

Contient le prompt système injecté au début de chaque conversation. Le prompt `expert` définit :
- Le rôle et la posture du LLM (expert de l'œuvre)
- Les règles absolues (ne pas inventer de citations, citer les sources)
- Le processus de réponse attendu (thinking → tool calls → réponse sourcée)
- Le format de sortie (texte + bloc sources avec `refId`, chapitre, page, URL)
- Les consignes de ton (accessible, poétique, précis)

### Section `developer`

Prompts utilisés en interne par les services (non visibles de l'utilisateur) :
- `titler` : instructions pour la génération de titre de conversation
- `title_user_template` : template pour formater le contexte envoyé au LLM lors du titrage

### Section `tool`

Descriptions des tools exposées au LLM via la définition MCP. Ces textes guident directement le comportement du modèle lors du choix et de l'usage des outils.

---

## Utilisation

```python
from prompts.loader import PromptLoader

# Chargement au démarrage de l'application (une seule fois)
PromptLoader.load("prompts/prompts.yaml")

# Accès par chemin hiérarchique avec interpolation de variables
system_prompt = PromptLoader.get("system", "expert", "content", book_title="Le Petit Prince")

titler_prompt = PromptLoader.get("developer", "titler", "content")

retriever_desc = PromptLoader.get("tool", "retriever", "description")
```

### Variables disponibles

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `{date}` | Date du jour (ISO) | Injectée automatiquement |
| `{book_title}` | `Le Petit Prince` | Titre de l'œuvre |
| `{author}` | `Antoine de Saint-Exupéry` | Auteur |

Les variables supplémentaires peuvent être passées en `**kwargs` à `PromptLoader.get()`.

---

## Structure

```
prompts/
├── pyproject.toml
├── prompts.yaml          # Registre de tous les prompts
└── src/prompts/
    ├── __init__.py
    └── loader.py         # PromptLoader (singleton statique)
```

---

## API du `PromptLoader`

```python
class PromptLoader:
    @classmethod
    def load(cls, path: str = "prompts/prompts.yaml") -> None:
        """Charge le registre YAML en mémoire. À appeler au démarrage."""
        ...

    @classmethod
    def get(cls, *keys: str, **variables) -> str:
        """
        Accède à un prompt par son chemin hiérarchique et interpole les variables.
        Lève KeyError si le chemin est invalide.
        Lève TypeError si le nœud cible n'est pas une chaîne.
        """
        ...
```

---

## Dépendances

```
pyaml >= 26.2.1
```
