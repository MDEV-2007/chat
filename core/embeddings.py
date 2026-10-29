"""Text embeddings via Ollama /api/embeddings, used for semantic memory search."""
import httpx

from core.config import OLLAMA_HOST

EMBEDDING_MODEL = "nomic-embed-text"


async def get_embedding(text: str) -> list[float] | None:
    if not text.strip():
        return None
    async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=30) as client:
        try:
            resp = await client.post(
                "/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": text}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding")
        except Exception:
            return None
