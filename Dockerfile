FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc binutils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts
RUN ./scripts/build_native.sh /build/native \
    && python -m pip wheel --wheel-dir /build/wheels .

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TVS_NATIVE_LIB=/app/native/libcombat.so \
    TVS_ROOM_TTL_SECONDS=7200 \
    TVS_MAX_ROOMS=1000

WORKDIR /app
RUN addgroup --system --gid 10001 game \
    && adduser --system --uid 10001 --ingroup game --home /app game

COPY --from=builder /build/wheels /tmp/wheels
RUN python -m pip install --no-cache-dir /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels
COPY --from=builder --chown=game:game /build/native/libcombat.so /app/native/libcombat.so

USER game
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

CMD ["uvicorn", "trump_vs_shakespeare.web.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
