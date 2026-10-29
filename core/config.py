"""App-wide config: defaults, paths, model metadata."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Packaged .exe: __file__ points into a temp extraction dir, so anchor
    # persistent data (chat history db) next to the executable instead.
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

DB_PATH = APP_DIR / "super_chat.db"

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"

# icon hint per model family, used by model switcher / auto-suggest
MODEL_KIND = {
    "qwen3-coder": "code",
    "qwen3": "chat",
    "llava": "vision",
    "moondream": "vision",
}

KIND_ICON = {
    "code": "</>",
    "vision": "\U0001F5BC️",
    "chat": "\U0001F4AC",
}

VISION_MODELS = ("llava", "moondream")


def guess_kind(model_name: str) -> str:
    base = model_name.split(":")[0]
    return MODEL_KIND.get(base, "chat")
