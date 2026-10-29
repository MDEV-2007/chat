"""Long-term semantic memory: embed messages, brute-force cosine search across past chats."""
import json
import math

from core import db
from core.embeddings import get_embedding

MIN_SCORE = 0.5
TOP_K = 4
MAX_SEARCHABLE_MESSAGES = 3000  # brute-force cap; fine at personal-app scale


async def embed_and_store_message(message_id: int, content: str) -> None:
    embedding = await get_embedding(content)
    if embedding:
        db.set_message_embedding(message_id, json.dumps(embedding))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def semantic_search(query_text: str, exclude_chat_id: int, top_k: int = TOP_K) -> list[dict]:
    query_embedding = await get_embedding(query_text)
    if not query_embedding:
        return []

    candidates = db.list_messages_with_embeddings(exclude_chat_id=exclude_chat_id)
    if not candidates:
        return []

    scored = []
    for row in candidates[-MAX_SEARCHABLE_MESSAGES:]:
        try:
            emb = json.loads(row["embedding"])
        except (TypeError, ValueError):
            continue
        score = _cosine(query_embedding, emb)
        if score >= MIN_SCORE:
            scored.append((score, row))

    scored.sort(key=lambda t: t[0], reverse=True)
    results = []
    for score, row in scored[:top_k]:
        results.append(
            {
                "score": score,
                "chat_title": row["chat_title"],
                "role": row["role"],
                "content": row["content"],
            }
        )
    return results


def format_memory_block(results: list[dict]) -> str:
    if not results:
        return ""
    lines = ["Relevant context recalled from earlier chats (may or may not be relevant, use judgement):"]
    for r in results:
        snippet = r["content"][:300]
        lines.append(f"- [{r['chat_title']}] ({r['role']}): {snippet}")
    return "\n".join(lines)
