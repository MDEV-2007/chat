"""Agent tool: run a shell command. No sandboxing — personal, local, full-control app."""
import asyncio
import subprocess

MAX_OUTPUT_CHARS = 8000
DEFAULT_TIMEOUT = 30


def _run_sync(command: str, cwd: str | None, timeout: int) -> dict:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-MAX_OUTPUT_CHARS:],
            "stderr": proc.stderr[-MAX_OUTPUT_CHARS:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Command timed out after {timeout}s"}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}


async def run_command(command: str, cwd: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    return await asyncio.to_thread(_run_sync, command, cwd, timeout)
