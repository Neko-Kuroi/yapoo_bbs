from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import RedirectResponse
from datetime import datetime
import sqlite3
from db import get_db
import math

from config import POSTS_PER_PAGE

router = APIRouter()

@router.post("/thread/{thread_id}/post")
async def add_post(
    thread_id: int,
    name: str = Form("anonymous"),
    content: str = Form(...)
):
    if not content.strip():
        raise HTTPException(status_code=400, detail="内容を入力してください")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:

        # スレッド存在確認（is_visible=1のみ）
        thread = conn.execute(
            'SELECT id FROM threads WHERE id = ? AND is_visible = 1',
            (thread_id,)
        ).fetchone()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # user_posts にINSERT
        conn.execute(
            '''INSERT INTO user_posts (thread_id, name, content, created_at, is_visible, status)
               VALUES (?, ?, ?, ?, 1, 'public')''',
            (thread_id, name or "anonymous", content.strip(), now)
        )

        # 書き込み後の総レス数を取得（ページ計算用）
        total_posts = conn.execute(
            'SELECT COUNT(*) FROM user_posts WHERE thread_id = ? AND is_visible = 1',
            (thread_id,)
        ).fetchone()[0]

        last_page = math.ceil(total_posts / POSTS_PER_PAGE) if total_posts > 0 else 1

    return RedirectResponse(
        url=f"/thread/{thread_id}?page={last_page}#post-{total_posts}",
        status_code=303
    )