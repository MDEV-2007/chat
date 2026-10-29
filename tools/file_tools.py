"""Agent tool: read/write local files. No path restriction — personal, local, full-control app."""
from pathlib import Path

MAX_READ_CHARS = 20000


def read_file(path: str) -> dict:
    try:
        p = Path(path).expanduser()
        content = p.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > MAX_READ_CHARS
        return {
            "ok": True,
            "content": content[:MAX_READ_CHARS],
            "truncated": truncated,
        }
    except Exception as ex:
        return {"ok": False, "error": str(ex)}


def write_file(path: str, content: str) -> dict:
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "bytes_written": len(content.encode("utf-8"))}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}
