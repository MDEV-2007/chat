# Super Chat

Shaxsiy lokal AI desktop chat — Ollama modellari bilan ishlaydi, cheklovsiz, to'liq nazorat sizda.

## Talablar

- Python 3.11+
- [Ollama](https://ollama.com) lokal ishga tushirilgan (`ollama serve`), kerakli modellar yuklangan:
  - `qwen3-coder:30b`
  - `qwen3:8b`
  - `llava:latest`
  - `moondream:latest`

## O'rnatish

```bash
pip install -r requirements.txt
```

## Ishga tushirish

```bash
python main.py
```

## Klaviatura tugmalari

- `Ctrl+N` — yangi chat
- `Esc` — streaming javobni to'xtatish

## Struktura

```
super-chat/
├── main.py
├── core/            # config, db (SQLite), ollama_client (async streaming)
├── ui/              # theme, sidebar, chat_view, model_switcher, input_bar
├── tools/           # v3: agent tools (bo'sh joy)
├── super_chat.db    # SQLite (avtomatik yaratiladi)
└── requirements.txt
```

## Bosqichlar

- **v1 (shu)**: streaming chat, model switcher, system prompt, SQLite tarix
- **v2**: rasm → llava/moondream avtomatik, uzoq muddatli semantik xotira (sqlite-vec/embedding)
- **v3**: agent/tool calling (fayl, terminal, veb qidiruv)
