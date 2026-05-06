import math
import html as html_lib
from fastapi import APIRouter, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from db import get_db
from config import API_KEY
from datetime import datetime


router = APIRouter()

ADMIN_POSTS_PER_PAGE = 50


def check_key(key: str):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")


# ========== 管理者：コメント一覧 ==========
@router.get("/admin/posts", response_class=HTMLResponse)
async def admin_posts(
    key: str = Query(...),
    page: int = Query(1, ge=1),
    status_filter: str = Query("all")
):
    check_key(key)

    with get_db() as conn:

        # フィルター条件
        if status_filter == "all":
            where = ""
            params_count = []
        else:
            where = "WHERE up.status = ? "
            params_count = [status_filter]

        # デバッグ用：これで 0 以外が出れば、where 句か JOIN が犯人です
        #debug_total = conn.execute("SELECT COUNT(*) FROM user_posts").fetchone()[0]
        #print(f"DEBUG: データベース内の生データ数 = {debug_total}")

        # 総件数
        total = conn.execute(
            "SELECT COUNT(*) FROM user_posts up " + where,
            params_count
        ).fetchone()[0]

        total_pages = math.ceil(total / ADMIN_POSTS_PER_PAGE) if total > 0 else 1
        page = max(1, min(page, total_pages))
        offset = (page - 1) * ADMIN_POSTS_PER_PAGE

        # コメント一覧（スレッドタイトルも取得）
        params_list = params_count + [ADMIN_POSTS_PER_PAGE, offset]
        posts = conn.execute(
            "SELECT up.id, up.name, up.content, up.created_at, "
            "up.status, up.is_visible, t.id as thread_id, t.title "
            "FROM user_posts up "
            "LEFT JOIN threads t ON t.id = up.thread_id "
            + where +
            " ORDER BY up.id DESC "
            "LIMIT ? OFFSET ?",
            params_list
        ).fetchall()

    html = generate_admin_posts_html(posts, page, total_pages, total, key, status_filter)
    return HTMLResponse(content=html)


# ========== 管理者：コメントのstatus変更 ==========
@router.post("/admin/posts/{post_id}/status")
async def update_post_status(
    post_id: int,
    key: str = Query(...),
    #status: str = Query(...),
    status: str = Form(...),
    page: int = Query(1),
    status_filter: str = Query("all")
):
    check_key(key)

    if status not in ("public", "hidden_temp", "hidden_perm", "spam"):
        raise HTTPException(status_code=400, detail="Invalid status")

    with get_db() as conn:
        cur = conn.execute(
            "UPDATE user_posts SET status = ? WHERE id = ?",
            (status, post_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post not found")

    return RedirectResponse(
        url=f"/admin/posts?key={key}&page={page}&status_filter={status_filter}",
        status_code=303
    )


# ========== HTML生成 ==========
def generate_admin_posts_html(posts, current_page, total_pages, total, key, status_filter):
    h = html_lib.escape

    status_colors = {
        "public":      "#28a745",
        "hidden_temp": "#fd7e14",
        "hidden_perm": "#dc3545",
        "spam":        "#6c757d",
    }
    status_labels = {
        "public":      "公開",
        "hidden_temp": "一時非表示",
        "hidden_perm": "非表示",
        "spam":        "スパム",
    }

    parts = []
    parts.append(f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>管理者 - コメント管理</title>
<style>
    body {{ font-family: sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; font-size: 13px; }}
    h1 {{ font-size: 20px; }}
    .filter-bar {{ margin: 15px 0; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .filter-btn {{ padding: 4px 12px; border-radius: 16px; text-decoration: none; font-size: 13px; color: #666; background: #f0f0f0; border: none; cursor: pointer; }}
    .filter-btn.active {{ background: #007bff; color: white; }}
    .info {{ background: #e7f3ff; padding: 8px 12px; margin: 10px 0; border-radius: 5px; }}
    table {{ width: 100%%; border-collapse: collapse; margin-top: 10px; }}
    th {{ background: #f8f9fa; padding: 8px; text-align: left; border-bottom: 2px solid #ddd; font-size: 12px; }}
    td {{ padding: 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
    tr:hover {{ background: #f9f9f9; }}
    .content-cell {{ max-width: 400px; word-break: break-all; }}
    .status-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; color: white; font-size: 11px; }}
    .status-form {{ display: flex; gap: 4px; flex-wrap: wrap; }}
    .btn {{ padding: 3px 8px; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; color: white; }}
    .btn-public      {{ background: #28a745; }}
    .btn-hidden_temp {{ background: #fd7e14; }}
    .btn-hidden_perm {{ background: #dc3545; }}
    .btn-spam        {{ background: #6c757d; }}
    .pagination {{ margin: 20px 0; text-align: center; }}
    .pagination a, .pagination span {{ display: inline-block; padding: 5px 10px; margin: 0 3px; border: 1px solid #ddd; text-decoration: none; }}
    .pagination .current {{ background: #007bff; color: white; border-color: #007bff; }}
    .pagination .disabled {{ color: #ccc; }}
    a {{ color: #007bff; text-decoration: none; }}
</style></head><body>
    <h1>🛠️ 管理者 - コメント管理</h1>
    <p><a href="/">← スレッド一覧</a></p>

    <div class="filter-bar">
        <span style="color:#666;">フィルター:</span>
""")

    for fkey, flabel in [("all", "すべて"), ("public", "公開"), ("hidden_temp", "一時非表示"), ("hidden_perm", "非表示"), ("spam", "スパム")]:
        active = "active" if status_filter == fkey else ""
        parts.append(f'<a href="/admin/posts?key={key}&status_filter={fkey}" class="filter-btn {active}">{flabel}</a>')

    parts.append(f"""
    </div>
    <div class="info">📊 総件数: {total}件 | 📄 ページ: {current_page}/{total_pages}</div>
    <table>
        <tr>
            <th>ID</th>
            <th>スレッド</th>
            <th>名前</th>
            <th>内容</th>
            <th>日時</th>
            <th>表示</th>
            <th>状態</th>
            <th>操作</th>
        </tr>
""")

    for post in posts:
        pid, name, content, created_at, status, is_visible, thread_id, thread_title = post
        ## フォーマット
        created_at_str = created_at.strftime('%Y-%m-%d %H:%M') if isinstance(created_at, datetime) else str(created_at or '')
        color = status_colors.get(status, "#999")
        label = status_labels.get(status, status)
        content_short = h(content[:100] + "..." if len(content) > 100 else content)
        visible_icon = "✅" if is_visible else "🚫"

        parts.append(f"""
        <tr>
            <td>{pid}</td>
            <td><a href="/thread/{thread_id}" target="_blank">{h((thread_title or '')[:30])}...</a></td>
            <td>{h(name or 'anonymous')}</td>
            <td class="content-cell">{content_short}</td>
            <td>{created_at_str}</td>
            <td style="text-align:center">{visible_icon}</td>
            <td><span class="status-badge" style="background:{color}">{label}</span></td>
            <td>
                <div class="status-form">
""")
        for s, sl in status_labels.items():
            if s != status:
                parts.append(f"""
                    <form method="post" action="/admin/posts/{pid}/status?key={key}&page={current_page}&status_filter={status_filter}" style="display:inline">
                        <input type="hidden" name="status" value="{s}">
                        <button type="submit" class="btn btn-{s}">{sl}</button>
                    </form>
""")
        parts.append("</div></td></tr>")

    parts.append("</table>")

    # ページネーション
    if total_pages > 1:
        parts.append('<div class="pagination">')
        if current_page > 1:
            parts.append(f'<a href="/admin/posts?key={key}&page=1&status_filter={status_filter}">« 最初</a>')
            parts.append(f'<a href="/admin/posts?key={key}&page={current_page-1}&status_filter={status_filter}">‹ 前へ</a>')
        else:
            parts.append('<span class="disabled">« 最初</span>')
            parts.append('<span class="disabled">‹ 前へ</span>')

        start_page = max(1, current_page - 5)
        end_page = min(total_pages, start_page + 9)
        for p in range(start_page, end_page + 1):
            if p == current_page:
                parts.append(f'<span class="current">{p}</span>')
            else:
                parts.append(f'<a href="/admin/posts?key={key}&page={p}&status_filter={status_filter}">{p}</a>')

        if current_page < total_pages:
            parts.append(f'<a href="/admin/posts?key={key}&page={current_page+1}&status_filter={status_filter}">次へ ›</a>')
            parts.append(f'<a href="/admin/posts?key={key}&page={total_pages}&status_filter={status_filter}">最後 »</a>')
        else:
            parts.append('<span class="disabled">次へ ›</span>')
            parts.append('<span class="disabled">最後 »</span>')
        parts.append('</div>')

    parts.append("</body></html>")
    return "".join(parts)