"""Agent tool: web search via DuckDuckGo HTML endpoint (no API key required)."""
import re

import httpx

RESULT_RE = re.compile(
    r'result__a"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
    r'result__snippet[^>]*>(?P<snippet>.*?)</a>',
    re.S,
)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return TAG_RE.sub("", text).strip()


async def search_web(query: str, max_results: int = 5) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            resp.encoding = "utf-8"
            results = []
            for m in RESULT_RE.finditer(resp.text):
                results.append(
                    {
                        "title": _clean(m.group("title")),
                        "url": m.group("url"),
                        "snippet": _clean(m.group("snippet")),
                    }
                )
                if len(results) >= max_results:
                    break
            return {"ok": True, "results": results}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}
