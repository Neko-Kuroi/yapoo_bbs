import os
from pathlib import Path

# DB設定
BASE_DIR = Path(__file__).parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "bbs.db"))

# ページネーション設定
THREADS_PER_PAGE = 20
POSTS_PER_PAGE = 20
SEARCH_RESULTS_PER_PAGE = 20

# 認証
API_KEY = os.getenv("API_KEY", "test-api-key-12345")