"""
Vercel Serverless Function - Flask WSGI adapter
"""
import os
import sys

# 프로젝트 루트를 path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Vercel 환경에서 토큰 캐시 경로를 /tmp로 변경
os.environ.setdefault("KIS_TOKEN_DIR", "/tmp/kis_config")

from stock_dashboard import app

# Vercel serverless handler
app.debug = False
