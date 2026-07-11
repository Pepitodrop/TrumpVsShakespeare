#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT_DIR="${1:-$ROOT/native}"
mkdir -p "$OUT_DIR"

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)
    SOURCE="$ROOT/src/trump_vs_shakespeare/native/combat_x86_64.S"
    ;;
  aarch64|arm64)
    SOURCE="$ROOT/src/trump_vs_shakespeare/native/combat_aarch64.S"
    ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

gcc -shared -fPIC -Wl,-z,relro,-z,now -o "$OUT_DIR/libcombat.so" "$SOURCE"
echo "Built $OUT_DIR/libcombat.so from $(basename "$SOURCE")"
