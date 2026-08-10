from __future__ import annotations

import os
from typing import Any

import uvicorn

APP_IMPORT = "trump_vs_shakespeare.web.app:app"


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _server_options() -> dict[str, Any]:
    return {
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": _int_env("PORT", 8000),
        "proxy_headers": True,
        "forwarded_allow_ips": os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
        "server_header": False,
        "ws_max_size": _int_env("WS_MAX_SIZE", 65536),
        "ws_max_queue": _int_env("WS_MAX_QUEUE", 16),
        "timeout_keep_alive": _int_env("KEEP_ALIVE_SECONDS", 5),
    }


def main() -> None:
    uvicorn.run(APP_IMPORT, **_server_options())


if __name__ == "__main__":
    main()
