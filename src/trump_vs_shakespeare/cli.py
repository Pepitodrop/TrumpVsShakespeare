from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "trump_vs_shakespeare.web.app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
        server_header=False,
        ws_max_size=int(os.getenv("WS_MAX_SIZE", "65536")),
        ws_max_queue=int(os.getenv("WS_MAX_QUEUE", "16")),
        timeout_keep_alive=int(os.getenv("KEEP_ALIVE_SECONDS", "5")),
    )


if __name__ == "__main__":
    main()
