"""
런타임 경로/환경 설정 공통 모듈
"""
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _resolve_path(value, default):
    path = value or default
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return os.path.normpath(path)


APP_CONFIG_DIR = _resolve_path(os.environ.get("APP_CONFIG_DIR"), BASE_DIR)
CONFIG_FILE = _resolve_path(
    os.environ.get("APP_CONFIG_FILE"),
    os.path.join(APP_CONFIG_DIR, "kis_devlp.yaml"),
)
ENV_FILE = _resolve_path(
    os.environ.get("APP_ENV_FILE"),
    os.path.join(APP_CONFIG_DIR, ".env"),
)
OHLCV_DIR = _resolve_path(
    os.environ.get("OHLCV_DIR"),
    os.path.join(BASE_DIR, "ohlcv_data"),
)
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "professai_stock_2026")
WEB_CONFIG_ENABLED = os.environ.get("WEB_CONFIG_ENABLED", "true").lower() in TRUTHY_VALUES


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
