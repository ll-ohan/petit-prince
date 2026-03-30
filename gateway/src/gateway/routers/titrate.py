import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from prompts import PromptLoader

from .. import settings
from ..schemas import TitrateRequest, TitrateResponse

logger = logging.getLogger("api_gateway.titrate")
router: APIRouter = APIRouter()


@router.post("/titrate", response_model=TitrateResponse)
async def generate_title(request: TitrateRequest) -> JSONResponse | TitrateResponse:
    """Génère un titre court pour la conversation en utilisant le prompt centralisé.

    Utilise 'developer.titler' pour le système et 'developer.title_user_template'
    pour formater l'entrée utilisateur.
    """
    try:
        system_content = PromptLoader.get("developer", "titler", "content")

        user_content = PromptLoader.get(
            "developer",
            "title_user_template",
            user_message=request.user_message,
            assistant_summary=request.assistant_summary or "...",
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        payload: dict[str, object] = {
            "model": settings.llm_model,
            "messages": messages,
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 50,
        }

        headers = (
            {"Authorization": f"Bearer {settings.llm_api_key}"}
            if settings.llm_api_key
            else {}
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            generated_title = data["choices"][0]["message"]["content"].strip()
            generated_title = generated_title.replace('"', "").replace("'", "")

            return TitrateResponse(title=generated_title)

    except (KeyError, ValueError) as e:
        logger.error(f"Erreur de configuration de prompts pour le titrage : {e}")
        return JSONResponse(
            content={"error": "Configuration prompts invalide"}, status_code=500
        )
    except Exception as e:
        logger.error(f"Échec de la génération de titre : {e}")
        return JSONResponse(
            content={"error": "Échec génération titre"}, status_code=500
        )
