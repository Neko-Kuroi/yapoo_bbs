import sqlite3
import logging
from contextlib import contextmanager

from config import DB_PATH

logger = logging.getLogger(__name__)

# 接続オプション
DB_OPTIONS = {
    "timeout": 10.0,  # ロック待機時間（秒）
}

# 接続時に毎回適用するPRAGMA
INIT_PRAGMAS = [
    "PRAGMA foreign_keys = ON",   # 外部キー制約有効化（ON DELETE CASCADEに必須）
    "PRAGMA journal_mode = WAL",  # 読み書きの並行性向上（読み多めの掲示板に有効）
    "PRAGMA synchronous = NORMAL",# WALモードとのバランス最適化
]


@contextmanager
def get_db():
    """
    SQLite接続を取得するコンテキストマネージャ。
    PRAGMAの適用・コミット・ロールバック・クローズを自動で処理する。

    使い方:
        with get_db() as conn:
            conn.execute("SELECT ...")
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, **DB_OPTIONS)

        for pragma in INIT_PRAGMAS:
            conn.execute(pragma)

        yield conn

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"DB transaction rolled back: {e}")
        raise

    finally:
        if conn:
            conn.close()