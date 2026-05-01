import sqlite3
from db import get_db
import math
import html as html_lib
import urllib.parse
from typing import Literal
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from config import THREADS_PER_PAGE
from ascii_art import ascii_art_cat

router = APIRouter()

SortType = Literal["new", "old", "posts", "updated", "views"]

# ========== スレッド一覧 ==========
@router.get("/", response_class=HTMLResponse)
async def index(
    page: int = Query(1, ge=1),
    sort: SortType = Query("new")
):
    with get_db() as conn:

        # ソート条件
        if sort == "new":
            order_by = "ORDER BY t.id DESC"
        elif sort == "old":
            order_by = "ORDER BY t.id ASC"
        elif sort == "posts":
            order_by = "ORDER BY res_count DESC, t.id DESC"
        elif sort == "updated":
            order_by = "ORDER BY t.last_post_at DESC, t.id DESC"
        elif sort == "views":
            order_by = "ORDER BY t.views DESC, t.id DESC"
        else:
            order_by = "ORDER BY t.id DESC"

        total_threads = conn.execute(
            'SELECT COUNT(*) FROM threads WHERE is_visible = 1'
        ).fetchone()[0]

        total_pages = math.ceil(total_threads / THREADS_PER_PAGE) if total_threads > 0 else 1
        page = max(1, min(page, total_pages))
        offset = (page - 1) * THREADS_PER_PAGE

        threads = conn.execute(f'''
            SELECT
                t.id,
                t.title,
                t.created_at,
                COUNT(p.id) as res_count,
                t.last_post_at,
                t.views
            FROM threads t
            LEFT JOIN user_posts p ON t.id = p.thread_id AND p.is_visible = 1
            WHERE t.is_visible = 1
            GROUP BY t.id
            {order_by}
            LIMIT ? OFFSET ?
        ''', (THREADS_PER_PAGE, offset)).fetchall()

    html = generate_index_html(threads, page, total_pages, total_threads, sort)
    return HTMLResponse(content=html)


# ========== スレッド一覧HTML生成 ==========
def generate_index_html(threads, current_page, total_pages, total_threads, current_sort):

    sort_btn = {
        "new":     "active" if current_sort == "new"     else "",
        "old":     "active" if current_sort == "old"     else "",
        "posts":   "active" if current_sort == "posts"   else "",
        "updated": "active" if current_sort == "updated" else "",
        "views":   "active" if current_sort == "views"   else "",
    }

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yapoo! ニュース掲示板</title>
    <style>
        body {{
            font-family: sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            font-size: 14px;
        }}
        h1 {{ font-size: 22px; }}
        h2 {{ font-size: 18px; }}

        .search-link {{ text-align: right; margin-bottom: 20px; }}
        .search-link a {{ color: #007bff; text-decoration: none; }}

        .sort-bar {{
            margin: 20px 0 15px 0;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .sort-label {{ font-size: 13px; color: #666; margin-right: 5px; }}
        .sort-btn {{
            background: none;
            border: none;
            padding: 4px 12px;
            border-radius: 16px;
            cursor: pointer;
            font-size: 13px;
            text-decoration: none;
            color: #666;
        }}
        .sort-btn:hover {{ background: #f0f0f0; color: #333; }}
        .sort-btn.active {{ background: #00a2ff; color: white; }}

        .thread {{ border-bottom: 1px solid #ddd; padding: 8px 0; }}
        .thread-title {{ font-size: 15px; }}
        .thread-title a {{ text-decoration: none; color: #007bff; }}
        .thread-title a:hover {{ text-decoration: underline; }}
        .thread-info {{ color: #666; font-size: 12px; margin-top: 4px; }}

        .search-links {{
            margin-top: 6px;
            font-size: 11px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .search-links a {{
            color: #888;
            text-decoration: none;
            padding: 2px 8px;
            border-radius: 12px;
            background: #f2f2f2;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}
        .search-links a:hover {{ background: #e0e0e0; color: #333; }}
        .search-links .google:hover {{ background: #4285f4; color: white; }}
        .search-links .yahoo-ai:hover {{ background: #ff6600; color: white; }}
        .search-links .yahoo-video:hover {{ background: #ff7600; color: white; }}

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
    <h1>🗨️ みんなの Yapoo! ニュース掲示板</h1>
    <div style="display: flex; align-items: center;">
        <img src="/static/yapoo.png" alt="Yapoo" height="30">
        <div style="margin-left: 8px;">
            <small>IDなしで、もっと便利に</small><br>
            <small>ヤプーニュース記事にコメントしにｬ-</small>
        </div>
    </div>
    <pre><small>{{ascii_art_cat}}</small></pre>

    <div class="sort-bar">
        <span class="sort-label">⇧⇩ 並べかえ:</span>
        <a href="/?sort=new"     class="sort-btn {sort_btn['new']}">🆕 新着順</a>
        <a href="/?sort=old"     class="sort-btn {sort_btn['old']}">📅 古い順</a>
        <a href="/?sort=posts"   class="sort-btn {sort_btn['posts']}">💬 レス数順</a>
        <a href="/?sort=updated" class="sort-btn {sort_btn['updated']}">🕐 更新順</a>
        <a href="/?sort=views"   class="sort-btn {sort_btn['views']}">🐾 閲覧数順</a>
    </div>

    <div class="info">
        📊 総スレッド数: {total_threads}件 |
        📄 ページ: {current_page}/{total_pages}
    </div>

    <h2>スレッド一覧</h2>
"""

    if not threads:
        html += "<p>まだスレッドがありません。</p>"
    else:
        for thread in threads:
            thread_id, title, created_at, res_count, last_post_at, views = thread

            search_query = urllib.parse.quote(title)
            google_url      = f"https://www.google.com/search?q={search_query}"
            yahoo_ai_url    = f"https://search.yahoo.co.jp/aichat?p={search_query}"
            yahoo_video_url = f"https://search.yahoo.co.jp/video/search?p={search_query}"

            html += f"""
    <div class="thread">
        <div class="thread-title">
            <a href="/thread/{thread_id}">{html_lib.escape(title)}</a>
        </div>
        <div class="thread-info">
            📅 {created_at} | 💬 {res_count}レス | 🐾 {views}ビュー | 🕐 最終更新: {last_post_at or created_at}
        </div>
        <div class="search-links">
            <a href="{google_url}" target="_blank" class="google">🔍 Google検索</a>
            <a href="{yahoo_ai_url}" target="_blank" class="yahoo-ai">🤖 Yahoo! AIチャット</a>
            <a href="{yahoo_video_url}" target="_blank" class="yahoo-video">📺 Yahoo!動画検索</a>
        </div>
    </div>
"""

    # ページネーション
    if total_pages > 1:
        html += '<div class="pagination">'
        if current_page > 1:
            html += f'<a href="/?sort={current_sort}&page=1">« 最初</a>'
            html += f'<a href="/?sort={current_sort}&page={current_page - 1}">‹ 前へ</a>'
        else:
            html += '<span class="disabled">« 最初</span>'
            html += '<span class="disabled">‹ 前へ</span>'

        start_page = max(1, current_page - 5)
        end_page = min(total_pages, start_page + 9)
        for p in range(start_page, end_page + 1):
            if p == current_page:
                html += f'<span class="current">{p}</span>'
            else:
                html += f'<a href="/?sort={current_sort}&page={p}">{p}</a>'

        if current_page < total_pages:
            html += f'<a href="/?sort={current_sort}&page={current_page + 1}">次へ ›</a>'
            html += f'<a href="/?sort={current_sort}&page={total_pages}">最後 »</a>'
        else:
            html += '<span class="disabled">次へ ›</span>'
            html += '<span class="disabled">最後 »</span>'
        html += '</div>'

    html += "</body></html>"
    return html
