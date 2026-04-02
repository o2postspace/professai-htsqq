#!/bin/sh
set -e

APP_CONFIG_DIR="${APP_CONFIG_DIR:-/app/runtime/config}"
KIS_TOKEN_DIR="${KIS_TOKEN_DIR:-/app/runtime/tokens}"
RUNTIME_OHLCV_DIR="${OHLCV_DIR:-/app/runtime/ohlcv}"
SEED_OHLCV_DIR="${SEED_OHLCV_DIR:-/app/ohlcv_deploy}"

mkdir -p "$APP_CONFIG_DIR" "$KIS_TOKEN_DIR" "$RUNTIME_OHLCV_DIR"

if [ -d "$SEED_OHLCV_DIR" ] && [ -z "$(find "$RUNTIME_OHLCV_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
  cp -R "$SEED_OHLCV_DIR"/. "$RUNTIME_OHLCV_DIR"/
fi

exec "$@"
