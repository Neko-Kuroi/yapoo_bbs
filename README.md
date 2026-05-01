# yapoo_bbs
# 04 - スレッドの表示処理（thread.py）

## このファイルの役割

`/thread/{thread_id}` にアクセスしたときのスレッドページを生成します。webhook本文の別枠表示、ユーザーコメントのページネーション、up/down投票数の表示、閲覧数のカウントを担当しています。

---

## 全体の流れ

```
ユーザーが /thread/1 にアクセス
    │
    ▼
スレッド情報を取得（is_visible=1のみ）
    │
    ├── 存在しない → 404エラー
    │
    ▼
views を +1（閲覧数カウント）
    │
    ▼
webhook_post を取得（別枠表示用、1件）
    │
    ▼
user_posts を取得（ページネーション付き）
    │
    ▼
votes を集計（表示中のuser_postsのup/down数）
    │
    ▼
HTMLを生成して返す
```

---

## クエリパラメータ

```python
@router.get("/thread/{thread_id}", response_class=HTMLResponse)
async def view_thread(
    thread_id: int,
    page: int = Query(1, ge=1)
):
```

`page` はURLの`?page=2`のような形で渡されるクエリパラメータです。

`Query(1, ge=1)` の意味は以下の通りです。

```
1    → デフォルト値（?pageがない場合は1ページ目）
ge=1 → greater than or equal to 1（1以上でなければエラー）
```

`response_class=HTMLResponse` は、このエンドポイントがHTMLを返すことをFastAPIに伝えます。デフォルトはJSONレスポンスです。

---

## 閲覧数のカウント

```python
conn.execute(
    'UPDATE threads SET views = views + 1 WHERE id = ?',
    (thread_id,)
)
```

スレッドの存在確認が通った後、アクセスのたびに`views`を1増やします。ログイン機能がないため同じ人が何度開いても+1されますが、「どのスレッドが人気か」を示す大まかな指標として機能します。

---

## webhook_postの取得（別枠表示）

```python
webhook_post = conn.execute(
    '''SELECT id, author, body, source_url, created_at
       FROM webhook_posts
       WHERE thread_id = ? AND is_visible = 1
       LIMIT 1''',
    (thread_id,)
).fetchone()
```

Webhookで作成されたニュース本文を取得します。`LIMIT 1`としているのは、設計上1スレッドに1件しか存在しないためです。

管理者が`webhook_post`を非表示（`is_visible=0`）にした場合、`webhook_post`は`None`になります。HTML生成側で`None`チェックをしているため、本文なしのスレッドとして表示されます。

---

## ページネーション計算

```python
total_posts = conn.execute(
    '''SELECT COUNT(*) FROM user_posts
       WHERE thread_id = ? AND is_visible = 1''',
    (thread_id,)
).fetchone()[0]

total_pages = math.ceil(total_posts / POSTS_PER_PAGE) if total_posts > 0 else 1
page = max(1, min(page, total_pages))
offset = (page - 1) * POSTS_PER_PAGE
```

ページネーションの計算は3ステップです。

```
1. total_pages の計算
   例: 45件、20件/ページ → ceil(45/20) = 3ページ

2. page の範囲チェック
   max(1, min(page, total_pages))
   → 0以下なら1、total_pagesより大きければtotal_pagesに丸める
   → 存在しないページを指定されても安全に処理できる

3. offset の計算
   (page - 1) * POSTS_PER_PAGE
   → 2ページ目なら (2-1) * 20 = 20件目からSELECT
```

---

## user_postsの取得

```python
user_posts = conn.execute(
    '''SELECT id, name, content, created_at
       FROM user_posts
       WHERE thread_id = ? AND is_visible = 1
       ORDER BY id ASC
       LIMIT ? OFFSET ?''',
    (thread_id, POSTS_PER_PAGE, offset)
).fetchall()
```

`ORDER BY id ASC` で投稿された順（古い順）に並べています。`LIMIT ? OFFSET ?` でそのページ分だけ取得します。

`fetchall()` はSELECT結果を全件リストで返します。`fetchone()`は1件だけ返します。

---

## votes の集計

```python
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
```

このクエリは工夫が必要な部分です。順番に説明します。

### post_ids と placeholders

```python
post_ids = [p[0] for p in user_posts]
# → [1, 2, 3, 4, 5] のようなIDのリスト

placeholders = ','.join('?' * len(post_ids))
# → "?,?,?,?,?" のような文字列
```

`IN (?)` の`?`はひとつの値しか受け取れないため、件数分の`?`を動的に生成しています。

### CASE WHEN による条件集計

```sql
SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END) as up_count
```

`CASE WHEN`はSQLの条件分岐です。`vote_type`が`'up'`なら1、それ以外なら0として合計することで、upの件数だけを数えています。downも同様です。これにより1回のクエリでup数とdown数を同時に取得できます。

### 辞書（dict）への変換

```python
votes = {}
for post_id, up, down in rows:
    votes[post_id] = (up, down)
```

`votes[post_id]`という形にしておくことで、HTML生成時に各コメントのup/down数を高速に取り出せます。

```python
# HTML生成側での使い方
up_count, down_count = votes.get(post_id, (0, 0))
# votesにpost_idがなければ(0, 0)をデフォルトとして返す
```

---

## HTML生成（generate_thread_html）

エンドポイントで集めたデータを`generate_thread_html`関数に渡してHTMLを生成します。

### webhook別枠の表示

```python
if webhook_post:
    wp_id, wp_author, wp_body, wp_source_url, wp_created_at = webhook_post
    webhook_html = f"""
<div class="webhook-post">
    <div class="webhook-header">
        📰 {wp_author} | {wp_created_at}
    </div>
    <div class="webhook-body">{wp_body.replace(chr(10), '<br>')}</div>
    ...
</div>
"""
```

`wp_body.replace(chr(10), '<br>')` は改行文字（`\n`）をHTMLの改行タグに変換します。`chr(10)`は改行文字のASCIIコードです。f文字列の中で`\n`を直接書くと構文エラーになる場合があるため、`chr(10)`を使っています。

### レス番号の計算

```python
for i, post in enumerate(user_posts):
    global_num = offset + i + 1
```

`enumerate`はリストをインデックス付きで取り出すPythonの組み込み関数です。`i`は0始まりなので+1しています。`offset`を加えることで、2ページ目なら21から始まるレス番号になります。

```
1ページ目: offset=0  → i=0,1,2... → global_num=1,2,3...
2ページ目: offset=20 → i=0,1,2... → global_num=21,22,23...
```

### ページネーションの重複表示

```python
{pagination_html}
{posts_html}
{pagination_html}
```

ページネーションをコメント一覧の上下両方に配置しています。同じ`pagination_html`を2回使うことで、コードの重複なく実現しています。

### ハッシュスクロール

```javascript
if (window.location.hash) {
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView();
}
```

URLに`#post-21`のようなハッシュがある場合、そのIDを持つ要素までスクロールします。`post.py`の書き込み後リダイレクトで`#post-{total_posts}`を付けているため、自分の投稿位置まで自動でスクロールされます。

`?.scrollIntoView()` の`?.`はオプショナルチェーンで、要素が存在しない場合にエラーにならないようにしています。

---

## まとめ

```
thread.py がやっていること

1. GET /thread/{thread_id} でスレッドページを返す
2. スレッド存在確認（is_visible=1のみ）
3. views を +1（閲覧数カウント）
4. webhook_post を取得（別枠表示、Noneの場合は非表示）
5. user_posts をページネーション付きで取得
6. 表示中のuser_postsのvotesを一括集計
7. HTMLを生成して返す

表示の構造
┌─────────────────────────────┐
│ webhook_post（ニュース別枠） │
└─────────────────────────────┘
  [ページネーション]
  1. コメント ▲0 ▼0
  2. コメント ▲3 ▼1
  ...
  [ページネーション]
  [書き込みフォーム]
```

次は `search.py` で、全文検索とソートの処理を見ていきます。