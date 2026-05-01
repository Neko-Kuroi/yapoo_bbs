from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sqlite3
from db import get_db

from auth import verify_api_key

router = APIRouter()

class NewsWebhook(BaseModel):
    title: str
    body: str
    source_url: Optional[str] = None
    author: Optional[str] = "ニュースBot"

@router.post("/webhook/news")
async def create_thread_from_news(
    news: NewsWebhook,
    api_key: str = Depends(verify_api_key)
):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:

        # 重複チェック（1時間以内に同じタイトル）
        recent = conn.execute(
            'SELECT id FROM threads WHERE title = ? AND created_at > datetime("now", "-1 hour")',
            (news.title,)
        ).fetchone()

        if recent:
            return {
                "status": "duplicate",
                "thread_id": recent[0],
                "message": "最近同じニュースのスレッドが作成されています"
            }

        # threads テーブルにINSERT
        cur = conn.execute(
            '''INSERT INTO threads (title, created_at, last_post_at, views, is_visible, status)
               VALUES (?, ?, ?, 0, 1, 'public')''',
            (news.title, now, now)
        )
        thread_id = cur.lastrowid

        # webhook_posts テーブルにINSERT
        conn.execute(
            '''INSERT INTO webhook_posts (thread_id, author, body, source_url, created_at, is_visible, status)
               VALUES (?, ?, ?, ?, ?, 1, 'public')''',
            (thread_id, news.author, news.body, news.source_url, now)
        )

    return {
        "status": "ok",
        "thread_id": thread_id,
        "title": news.title,
        "url": f"/thread/{thread_id}"
    }

@router.get("/webhook/test")
async def test_webhook():
    return {
        "message": "Webhookエンドポイントが動作しています",
    }

@router.get("/webhook/check-key")
async def check_api_key(api_key: str = Depends(verify_api_key)):
    return {"message": "API key is valid!"}