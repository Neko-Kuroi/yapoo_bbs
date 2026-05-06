from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from db import get_db

router = APIRouter()

# GETからPOSTに変更し、ブラウザの先読みや誤爆を防ぐ
@router.post("/vote/{post_id}/{vote_type}")
async def add_vote(post_id: int, vote_type: str):

    if vote_type not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Invalid vote type")

    with get_db() as conn:
        # post_idが存在するか確認
        row = conn.execute(
            "SELECT thread_id FROM user_posts WHERE id = ? AND is_visible = 1",
            (post_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Post not found")

        thread_id = row[0]

        # votesにINSERT
        conn.execute(
            "INSERT INTO votes (post_id, vote_type, created_at) VALUES (?, ?, datetime('now'))",
            (post_id, vote_type)
        )

    # voted フラグ + ハッシュ（#post-id）
    return RedirectResponse(
        url=f"/thread/{thread_id}?voted=1#post-{post_id}", # フラグを付与
        status_code=303
    )