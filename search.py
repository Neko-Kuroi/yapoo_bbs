import sqlite3
from db import get_db
import math
import html as html_lib
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from config import SEARCH_RESULTS_PER_PAGE
from ascii_art import ascii_art_cat2

router = APIRouter()

# ========== 検索エンドポイント ==========
@router.get("/search", response_class=HTMLResponse)
async def search_posts(
    q: Optional[str] = Query(None),
    sort: str = Query("hits"),
    page: int = Query(1, ge=1)
):
    results = []
    total_results = 0
    total_pages = 1
    search_query = q.strip() if q else ""

    if search_query:
        keywords = search_query.replace("　", " ").split()

        # 3文字以上 → FTS5 trigram
        # 2文字以下 → LIKE フォールバック
        long_keywords  = [k for k in keywords if len(k) >= 3]
        short_keywords = [k for k in keywords if len(k) < 3]

        with get_db() as conn:

            # ソート条件
            if sort == "hits":
                order_by = "ORDER BY hit_count DESC, t.last_post_at DESC"
            elif sort == "new":
                order_by = "ORDER BY t.last_post_at DESC"
            elif sort == "old":
                order_by = "ORDER BY t.last_post_at ASC"
            elif sort == "posts":
                order_by = "ORDER BY total_posts DESC, t.last_post_at DESC"
            else:
                order_by = "ORDER BY hit_count DESC, t.last_post_at DESC"

            if long_keywords:
                # FTS5検索（3文字以上）
                match_expr = " AND ".join(f'"{k}"' for k in long_keywords)

                # 2文字以下のLIKE追加条件
                like_conditions = ""
                like_params = []
                if short_keywords:
                    clauses = []
                    for k in short_keywords:
                        clauses.append("(snippet.content LIKE ? OR t.title LIKE ?)")
                        like_params.extend([f"%{k}%", f"%{k}%"])
                    like_conditions = "AND " + " AND ".join(clauses)

                # スレッド単位で集計
                sql = f'''
                    SELECT
                        t.id,
                        t.title,
                        t.last_post_at,
                        t.views,
                        COUNT(pf.post_id) as hit_count,
                        (SELECT COUNT(*) FROM user_posts up2
                         WHERE up2.thread_id = t.id AND up2.is_visible = 1) as total_posts,
                        (SELECT pf2.content
                         FROM posts_fts pf2
                         WHERE pf2.post_id IN (
                             SELECT id FROM user_posts WHERE thread_id = t.id
                             UNION
                             SELECT id FROM webhook_posts WHERE thread_id = t.id
                         )
                         AND pf2.content MATCH ?
                         LIMIT 1) as snippet
                    FROM posts_fts pf
                    JOIN (
                        SELECT id AS post_id, thread_id, content FROM user_posts WHERE is_visible = 1
                        UNION ALL
                        SELECT id AS post_id, thread_id, body AS content FROM webhook_posts WHERE is_visible = 1
                    ) AS snippet ON snippet.post_id = pf.post_id
                    JOIN threads t ON t.id = snippet.thread_id
                    WHERE pf.content MATCH ?
                    AND t.is_visible = 1
                    {like_conditions}
                    GROUP BY t.id
                    {order_by}
                    LIMIT ? OFFSET ?
                '''

                # 総スレッド件数
                count_sql = f'''
                    SELECT COUNT(DISTINCT t.id)
                    FROM posts_fts pf
                    JOIN (
                        SELECT id AS post_id, thread_id, content FROM user_posts WHERE is_visible = 1
                        UNION ALL
                        SELECT id AS post_id, thread_id, body AS content FROM webhook_posts WHERE is_visible = 1
                    ) AS snippet ON snippet.post_id = pf.post_id
                    JOIN threads t ON t.id = snippet.thread_id
                    WHERE pf.content MATCH ?
                    AND t.is_visible = 1
                    {like_conditions}
                '''

                total_results = conn.execute(
                    count_sql, [match_expr] + like_params
                ).fetchone()[0]

                total_pages = math.ceil(total_results / SEARCH_RESULTS_PER_PAGE) if total_results > 0 else 1
                page = max(1, min(page, total_pages))
                offset = (page - 1) * SEARCH_RESULTS_PER_PAGE

                results = conn.execute(
                    sql,
                    [match_expr]               # snippetサブクエリのMATCH
                    + [match_expr]             # WHERE pf.content MATCH
                    + like_params              # LIKE追加条件
                    + [SEARCH_RESULTS_PER_PAGE, offset]  # LIMIT OFFSET
                ).fetchall()

            else:
                # 全て2文字以下 → LIKEのみ
                clauses = []
                params = []
                for k in short_keywords:
                    clauses.append("(up.content LIKE ? OR t.title LIKE ?)")
                    params.extend([f"%{k}%", f"%{k}%"])
                where_clause = " AND ".join(clauses)

                count_sql = f'''
                    SELECT COUNT(DISTINCT t.id)
                    FROM (
                        SELECT thread_id, content FROM user_posts WHERE is_visible = 1
                        UNION ALL
                        SELECT thread_id, body AS content FROM webhook_posts WHERE is_visible = 1
                    ) AS up
                    JOIN threads t ON t.id = up.thread_id
                    WHERE t.is_visible = 1 AND ({where_clause})
                '''
                total_results = conn.execute(count_sql, params).fetchone()[0]
                total_pages = math.ceil(total_results / SEARCH_RESULTS_PER_PAGE) if total_results > 0 else 1
                page = max(1, min(page, total_pages))
                offset = (page - 1) * SEARCH_RESULTS_PER_PAGE

                sql = f'''
                    SELECT
                        t.id,
                        t.title,
                        t.last_post_at,
                        t.views,
                        COUNT(*) as hit_count,
                        (SELECT COUNT(*) FROM user_posts up2
                         WHERE up2.thread_id = t.id AND up2.is_visible = 1) as total_posts,
                        up.content as snippet
                    FROM (
                        SELECT thread_id, content FROM user_posts WHERE is_visible = 1
                        UNION ALL
                        SELECT thread_id, body AS content FROM webhook_posts WHERE is_visible = 1
                    ) AS up
                    JOIN threads t ON t.id = up.thread_id
                    WHERE t.is_visible = 1 AND ({where_clause})
                    GROUP BY t.id
                    {order_by}
                    LIMIT ? OFFSET ?
                '''
                results = conn.execute(sql, params + [SEARCH_RESULTS_PER_PAGE, offset]).fetchall()

    html = generate_search_html(search_query, results, page, total_pages, total_results, sort)
    return HTMLResponse(content=html)


# ========== 検索HTML生成 ==========
def generate_search_html(query, results, current_page, total_pages, total_results, current_sort):

    search_value = query if query else ""

    # ソートボタン
    sort_labels = {
        "hits":  "🔍 ヒット数順",
        "new":   "🕐 新着順",
        "old":   "📅 古い順",
        "posts": "💬 レス数順",
    }
    sort_bar = ""
    for key, label in sort_labels.items():
        active = "active" if current_sort == key else ""
        sort_bar += f'<a href="/search?q={query}&sort={key}" class="sort-btn {active}">{label}</a>'

    results_section = ""

    if query:
        if not results:
            results_section = f"""
            <div class="no-results">
                😢 「{html_lib.escape(query)}」に一致するスレッドは見つかりませんでした<br>
                <small>違うキーワードで試してみてください</small>
            </div>
            """
        else:
            for row in results:
                thread_id, title, last_post_at, views, hit_count, total_posts, snippet = row
                snippet_text = snippet[:250] + "..." if snippet and len(snippet) > 250 else (snippet or "")
                snippet_html = html_lib.escape(snippet_text)

                results_section += f"""
<div class="result">
    <div class="result-title">
        <a href="/thread/{thread_id}">📌 {html_lib.escape(title)}</a>
    </div>
    <div class="result-meta">
        🔍 {hit_count}件ヒット | 💬 {total_posts}レス | 🐾 {views}ビュー | 🕐 {last_post_at}
    </div>
    <div class="result-snippet">{snippet_html}</div>
</div>
"""

            # ページネーション
            if total_pages > 1:
                results_section += '<div class="pagination">'
                if current_page > 1:
                    results_section += f'<a href="/search?q={query}&sort={current_sort}&page=1">« 最初</a>'
                    results_section += f'<a href="/search?q={query}&sort={current_sort}&page={current_page-1}">‹ 前へ</a>'
                start_page = max(1, current_page - 5)
                end_page = min(total_pages, start_page + 9)
                for p in range(start_page, end_page + 1):
                    if p == current_page:
                        results_section += f'<span class="current">{p}</span>'
                    else:
                        results_section += f'<a href="/search?q={query}&sort={current_sort}&page={p}">{p}</a>'
                if current_page < total_pages:
                    results_section += f'<a href="/search?q={query}&sort={current_sort}&page={current_page+1}">次へ ›</a>'
                    results_section += f'<a href="/search?q={query}&sort={current_sort}&page={total_pages}">最後 »</a>'
                results_section += '</div>'

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>検索 - Yapoo掲示板</title>
    <style>
        body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; font-size: 14px; }}
        h1 {{ font-size: 22px; }}
        .search-section {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; border: 1px solid #ddd; }}
        .search-box {{ display: flex; gap: 10px; }}
        .search-box input {{ flex: 1; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 8px; }}
        .search-box button {{ padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }}
        .search-box button:hover {{ background: #0056b3; }}
        .sort-bar {{ margin: 15px 0; display: flex; gap: 8px; flex-wrap: wrap; }}
        .sort-btn {{ background: none; border: none; padding: 4px 12px; border-radius: 16px; cursor: pointer; font-size: 13px; text-decoration: none; color: #666; }}
        .sort-btn:hover {{ background: #f0f0f0; }}
        .sort-btn.active {{ background: #00a2ff; color: white; }}
        .result {{ border-bottom: 1px solid #ddd; padding: 15px 0; }}
        .result-title {{ font-size: 16px; margin-bottom: 6px; }}
        .result-title a {{ text-decoration: none; color: #007bff; }}
        .result-title a:hover {{ text-decoration: underline; }}
        .result-meta {{ color: #666; font-size: 12px; margin-bottom: 6px; }}
        .result-snippet {{ color: #555; font-size: 13px; line-height: 1.5; }}
        .pagination {{ margin: 20px 0; text-align: center; }}
        .pagination a, .pagination span {{ display: inline-block; padding: 5px 10px; margin: 0 3px; border: 1px solid #ddd; text-decoration: none; }}
        .pagination .current {{ background-color: #007bff; color: white; border-color: #007bff; }}
        .info {{ background: #e7f3ff; padding: 8px 12px; margin: 10px 0; border-radius: 5px; }}
        .no-results {{ text-align: center; padding: 40px; color: #666; }}
        .back-link {{ display: inline-block; margin: 20px 0; color: #007bff; text-decoration: none; }}
        .tips {{ margin-top: 15px; font-size: 12px; color: #666; }}
        code {{ background: #e0e0e0; padding: 2px 6px; border-radius: 4px; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🔍 掲示板 スレッドを検索</h1>
    <pre><small>{ascii_art_cat2}</small></pre>
    <p><a href="/" class="back-link">← スレッド一覧に戻る</a></p>

    <div class="search-section">
        <form class="search-box" method="get" action="/search">
            <input type="text" name="q" value="{search_value}" placeholder="検索キーワードを入力..." autofocus>
            <button type="submit">検索</button>
        </form>
        <div class="tips">
            💡 3文字以上: 全文検索 | 2文字以下: 部分一致検索 | スペース区切りでAND検索
        </div>
    </div>
"""

    if query:
        html += f"""
    <div class="info">
        📊 {total_results}スレッドでヒット（「{query}」）
    </div>
    <div class="sort-bar">
        <span style="font-size:13px; color:#666;">⇧⇩ 並べかえ:</span>
        {sort_bar}
    </div>
    {results_section}
"""
    else:
        html += '<div class="info">💡 キーワードを入力して検索してください</div>'

    html += "</body></html>"
    return html
