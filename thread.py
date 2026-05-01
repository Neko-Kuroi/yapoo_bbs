import sqlite3
from db import get_db
import math
import html as html_lib
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from config import POSTS_PER_PAGE
from ascii_art import ascii_art_cat3

router = APIRouter()

# ========== スレッド表示 ==========
@router.get("/thread/{thread_id}", response_class=HTMLResponse)
async def view_thread(
    thread_id: int,
    page: int = Query(1, ge=1)
):
    with get_db() as conn:

        # スレッド取得（is_visible=1のみ）
        thread = conn.execute(
            '''SELECT id, title, created_at
               FROM threads
               WHERE id = ? AND is_visible = 1''',
            (thread_id,)
        ).fetchone()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # アクセス時にviews+1
        conn.execute(
            'UPDATE threads SET views = views + 1 WHERE id = ?',
            (thread_id,)
        )

        # webhook_posts（別枠表示用、1件）
        webhook_post = conn.execute(
            '''SELECT id, author, body, source_url, created_at
               FROM webhook_posts
               WHERE thread_id = ? AND is_visible = 1
               LIMIT 1''',
            (thread_id,)
        ).fetchone()

        # user_postsの総数（ページネーション用）
        total_posts = conn.execute(
            '''SELECT COUNT(*) FROM user_posts
               WHERE thread_id = ? AND is_visible = 1''',
            (thread_id,)
        ).fetchone()[0]

        total_pages = math.ceil(total_posts / POSTS_PER_PAGE) if total_posts > 0 else 1
        page = max(1, min(page, total_pages))
        offset = (page - 1) * POSTS_PER_PAGE

        # user_posts取得
        user_posts = conn.execute(
            '''SELECT id, name, content, created_at
               FROM user_posts
               WHERE thread_id = ? AND is_visible = 1
               ORDER BY id ASC
               LIMIT ? OFFSET ?''',
            (thread_id, POSTS_PER_PAGE, offset)
        ).fetchall()

        # user_postsのvotes集計
        votes = {}
        if user_posts:
            post_ids = [p[0] for p in user_posts]
            placeholders = ','.join('?' * len(post_ids))
            rows = conn.execute(f'''
                SELECT
                    post_id,
                    SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END) as up_count,
                    SUM(CASE WHEN vote_type = 'down' THEN 1 ELSE 0 END) as down_count
                FROM votes
                WHERE post_id IN ({placeholders})
                GROUP BY post_id
            ''', post_ids).fetchall()
            for post_id, up, down in rows:
                votes[post_id] = (up, down)

    html = generate_thread_html(
        thread, webhook_post, user_posts, votes,
        thread_id, page, total_pages, total_posts, offset
    )
    return HTMLResponse(content=html)


# ========== スレッド表示HTML生成 ==========
def generate_thread_html(thread, webhook_post, user_posts, votes, thread_id, current_page, total_pages, total_posts, offset):

    # webhook_posts 別枠HTML
    webhook_html = ""
    if webhook_post:
        wp_id, wp_author, wp_body, wp_source_url, wp_created_at = webhook_post
        source_html = f'<div class="source-url">📌 出典: <a href="{wp_source_url}" target="_blank">{wp_source_url}</a></div>' if wp_source_url else ""
        webhook_html = f"""
    <div class="webhook-post">
        <div class="webhook-header">
            📰 {wp_author} &nbsp;|&nbsp; {wp_created_at}
        </div>
        <div class="webhook-body">{html_lib.escape(wp_body).replace(chr(10), '<br>')}</div>
        {source_html}
    </div>
"""

    # user_posts HTML
    posts_html = ""
    for i, post in enumerate(user_posts):
        post_id, name, content, created_at = post
        global_num = offset + i + 1
        up_count, down_count = votes.get(post_id, (0, 0))
        content_html = html_lib.escape(content).replace('\n', '<br>')

        posts_html += f"""
    <div class="post" id="post-{global_num}">
        <div class="post-header">
            <span class="res-number">{global_num}</span> :
            <strong>{name or 'anonymous'}</strong>
            ({created_at})
        </div>
        <div class="post-content">{content_html}</div>
        <div class="post-votes">
            <a href="/vote/{post_id}/up" class="vote-btn up">▲ {up_count}</a>
            <a href="/vote/{post_id}/down" class="vote-btn down">▼ {down_count}</a>
        </div>
    </div>
"""

    # ページネーション
    pagination_html = ""
    if total_pages > 1:
        pagination_html += '<div class="pagination">'
        if current_page > 1:
            pagination_html += f'<a href="?page=1">« 最初</a>'
            pagination_html += f'<a href="?page={current_page - 1}">‹ 前へ</a>'
        else:
            pagination_html += '<span class="disabled">« 最初</span>'
            pagination_html += '<span class="disabled">‹ 前へ</span>'

        start_page = max(1, current_page - 5)
        end_page = min(total_pages, start_page + 9)
        for p in range(start_page, end_page + 1):
            if p == current_page:
                pagination_html += f'<span class="current">{p}</span>'
            else:
                pagination_html += f'<a href="?page={p}">{p}</a>'

        if current_page < total_pages:
            pagination_html += f'<a href="?page={current_page + 1}">次へ ›</a>'
            pagination_html += f'<a href="?page={total_pages}">最後 »</a>'
        else:
            pagination_html += '<span class="disabled">次へ ›</span>'
            pagination_html += '<span class="disabled">最後 »</span>'
        pagination_html += '</div>'

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{thread[1]} - 掲示板</title>
    <style>
        body {{
            font-family: sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            font-size: 14px;
            line-height: 1.5;
        }}
        h1 {{ font-size: 20px; margin-bottom: 10px; }}
        h2 {{ font-size: 18px; margin-top: 20px; }}

        .search-link {{ text-align: right; margin-bottom: 20px; }}
        .search-link a {{ color: #007bff; text-decoration: none; }}

        /* webhook別枠 */
        .webhook-post {{
            background: #f0f7ff;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .webhook-header {{
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #cce0ff;
        }}
        .webhook-body {{
            font-size: 14px;
            line-height: 1.7;
        }}
        .source-url {{
            margin-top: 10px;
            font-size: 12px;
            color: #555;
        }}
        .source-url a {{ color: #007bff; }}

        /* user_posts */
        .post {{
            border: 1px solid #ddd;
            margin: 8px 0;
            padding: 8px 12px;
            background: #fff;
        }}
        .post-header {{
            color: #666;
            margin-bottom: 8px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
            font-size: 11px;
        }}
        .res-number {{ font-weight: bold; color: #00f; }}
        .post-content {{
            white-space: pre-wrap;
            line-height: 1.5;
            font-size: 14px;
        }}
        .post-votes {{
            margin-top: 8px;
            font-size: 12px;
        }}
        .vote-btn {{
            display: inline-block;
            padding: 2px 10px;
            margin-right: 6px;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-decoration: none;
            color: #555;
        }}
        .vote-btn.up:hover {{ background: #e8f5e9; color: #2e7d32; border-color: #2e7d32; }}
        .vote-btn.down:hover {{ background: #fce4ec; color: #c62828; border-color: #c62828; }}

        .pagination {{ margin: 20px 0; text-align: center; font-size: 13px; }}
        .pagination a, .pagination span {{
            display: inline-block;
            padding: 5px 10px;
            margin: 0 3px;
            border: 1px solid #ddd;
            text-decoration: none;
        }}
        .pagination a:hover {{ background-color: #f0f0f0; }}
        .pagination .current {{ background-color: #007bff; color: white; border-color: #007bff; }}
        .pagination .disabled {{ color: #ccc; }}

        textarea {{ width: 100%; height: 80px; font-size: 13px; box-sizing: border-box; }}
        input[type=text] {{ width: 100%; max-width: 250px; font-size: 13px; }}
        .btn {{
            margin-top: 10px;
            padding: 5px 15px;
            background: #007bff;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 13px;
        }}
        .btn:hover {{ background: #0056b3; }}
        .info {{
            background: #e7f3ff;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 5px;
            font-size: 13px;
        }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="search-link">
        🔍 <a href="/search">掲示板 スレッドを検索</a>
    </div>
    <h1>{thread[1]}</h1>
    <p><a href="/">← スレッド一覧に戻る</a></p>

    {webhook_html}

    <div class="info">
        💬 コメント数: {total_posts}件 |
        📄 ページ: {current_page}/{total_pages}
    </div>

    {pagination_html}
    {posts_html}
    {pagination_html}

    <h2>📝 カキコむ</h2>
    <pre><small>{ascii_art_cat3}</small></pre>

    <form method="post" action="/thread/{thread_id}/post">
        <div>
            <label>名前:</label><br>
            <input type="text" name="name" placeholder="anonymous" value="anonymous" maxlength="50">
        </div>
        <div style="margin-top: 10px;">
            <label>本文:</label><br>
            <textarea name="content" required maxlength="2000"></textarea>
        </div>
        <button type="submit" class="btn">書き込む</button>
    </form>

    <script>
        if (window.location.hash) {{
            document.getElementById(window.location.hash.slice(1))?.scrollIntoView();
        }}
    </script>
</body>
</html>
"""
    return html