ARG PYTHON_IMAGE=python:3.12-slim-bookworm@sha256:8a7e7cc04fd3e2bd787f7f24e22d5d119aa590d429b50c95dfe12b3abe52f48b

FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc binutils libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE constraints.txt ./
COPY src ./src
COPY scripts ./scripts
RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --constraint constraints.txt pip setuptools wheel \
    && ./scripts/build_native.sh /build/native \
    && /opt/venv/bin/python -m pip install --constraint constraints.txt --no-compile . \
    && /opt/venv/bin/python -m pip check

FROM ${PYTHON_IMAGE} AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TVS_NATIVE_LIB=/app/native/libcombat.so \
    TVS_ROOM_TTL_SECONDS=7200 \
    TVS_MAX_ROOMS=1000 \
    TVS_MAX_SOCKETS_PER_ROOM=6 \
    TVS_SOCKET_SEND_TIMEOUT_SECONDS=3 \
    TVS_WS_IDLE_TIMEOUT_SECONDS=60 \
    TVS_WS_MESSAGES_PER_WINDOW=40 \
    TVS_WS_RATE_WINDOW_SECONDS=10 \
    FORWARDED_ALLOW_IPS=127.0.0.1

WORKDIR /app
RUN addgroup --system --gid 10001 game \
    && adduser --system --uid 10001 --ingroup game --no-create-home --home /nonexistent game \
    && mkdir -p /app/native \
    && chown -R game:game /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=game:game /build/native/libcombat.so /app/native/libcombat.so

USER game
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD /opt/venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"

CMD ["trump-vs-shakespeare"]
