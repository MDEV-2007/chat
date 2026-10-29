"""Tool schemas (Ollama function-calling format) + dispatch."""
from tools.file_tools import read_file, write_file
from tools.terminal_tool import run_command
from tools.web_search_tool import search_web

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a local text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a local text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command on the user's machine and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "cwd": {"type": "string", "description": "Working directory (optional)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web and return a list of {title, url, snippet} results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
]


async def execute_tool(name: str, args: dict) -> dict:
    try:
        if name == "read_file":
            return read_file(args["path"])
        if name == "write_file":
            return write_file(args["path"], args.get("content", ""))
        if name == "run_command":
            return await run_command(args["command"], args.get("cwd"))
        if name == "search_web":
            return await search_web(args["query"])
        return {"ok": False, "error": f"Unknown tool: {name}"}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}
