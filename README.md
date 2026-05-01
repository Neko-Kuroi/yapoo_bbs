# FastAPI + SQLite で作る掲示板チュートリアル

## このチュートリアルについて

このチュートリアルでは、FastAPIとSQLiteを使ったシンプルな掲示板アプリの設計と実装を解説します。

外部スクリプトからWebhookでニュース記事をスレッドとして投稿し、ユーザーがコメントを書き込めるスレッドフロート型の掲示板です。ログイン機能のないシンプルな構成を出発点に、全文検索・閲覧数・up/down評価・管理者機能を持つ設計になっています。

**対象読者**

- PythonでWebアプリを作ったことがある
- FastAPIは初めて
- SQLiteのFTS全文検索は初めて

---

## 目次

  - [このチュートリアルについて](#このチュートリアルについて)
  - [技術スタック](#技術スタック)
  - [ファイル構成](#ファイル構成)
  - [ページ構成](#ページ構成)
  - [DB設計の全体像](#db設計の全体像)
  - [app.py（起動ファイル）](#apppy（起動ファイル）)
- [01 - データベースの設計と初期化（init_db.py）](#01---データベースの設計と初期化（init_dbpy）)
  - [このファイルの役割](#このファイルの役割)
  - [テーブル構成の全体像](#テーブル構成の全体像)
  - [外部キー制約の有効化](#外部キー制約の有効化)
  - [各テーブルの詳細](#各テーブルの詳細)
  - [FTS5 全文検索テーブル（posts_fts）](#fts5-全文検索テーブル（posts_fts）)
  - [トリガー](#トリガー)
  - [インデックス](#インデックス)
  - [CREATE TABLE IF NOT EXISTS について](#create-table-if-not-exists-について)
  - [まとめ](#まとめ)
- [02 - Webhookでスレッドを作成する（webhook.py）](#02---webhookでスレッドを作成する（webhookpy）)
  - [このファイルの役割](#このファイルの役割)
  - [全体の流れ](#全体の流れ)
  - [APIキー認証](#apiキー認証)
- [auth.py のイメージ](#authpy-のイメージ)
  - [リクエストの形式（Pydanticモデル）](#リクエストの形式（pydanticモデル）)
  - [重複チェック](#重複チェック)
  - [DBへの書き込み](#dbへの書き込み)
- [threadsテーブルにINSERT](#threadsテーブルにinsert)
- [webhook_postsテーブルにINSERT](#webhook_postsテーブルにinsert)
  - [レスポンス](#レスポンス)
  - [確認用エンドポイント](#確認用エンドポイント)
  - [APIRouterとは](#apirouterとは)
- [app.py でのインクルードイメージ](#apppy-でのインクルードイメージ)
  - [外部スクリプトからの呼び出し例](#外部スクリプトからの呼び出し例)
- [→ {"status": "ok", "thread_id": 1, "url": "/thread/1", ...}](#→-{"status":-"ok",-"thread_id":-1,-"url":-"thread1",-})
  - [まとめ](#まとめ)
- [03 - ユーザーの書き込み処理（post.py）](#03---ユーザーの書き込み処理（postpy）)
  - [このファイルの役割](#このファイルの役割)
  - [全体の流れ](#全体の流れ)
  - [エンドポイントの定義](#エンドポイントの定義)
  - [バリデーション](#バリデーション)
  - [スレッドの存在確認](#スレッドの存在確認)
  - [DBへの書き込み](#dbへの書き込み)
  - [最終ページへのリダイレクト](#最終ページへのリダイレクト)
  - [POSTS_PER_PAGE とは](#posts_per_page-とは)
  - [まとめ](#まとめ)
- [04 - スレッドの表示処理（thread.py）](#04---スレッドの表示処理（threadpy）)
  - [このファイルの役割](#このファイルの役割)
  - [全体の流れ](#全体の流れ)
  - [クエリパラメータ](#クエリパラメータ)
  - [閲覧数のカウント](#閲覧数のカウント)
  - [webhook_postの取得（別枠表示）](#webhook_postの取得（別枠表示）)
  - [ページネーション計算](#ページネーション計算)
  - [user_postsの取得](#user_postsの取得)
  - [votes の集計](#votes-の集計)
- [→ [1, 2, 3, 4, 5] のようなIDのリスト](#→-[1,-2,-3,-4,-5]-のようなidのリスト)
- [→ "?,?,?,?,?" のような文字列](#→-"?,?,?,?,?"-のような文字列)
- [HTML生成側での使い方](#html生成側での使い方)
- [votesにpost_idがなければ(0, 0)をデフォルトとして返す](#votesにpost_idがなければ0,-0をデフォルトとして返す)
  - [HTML生成（generate_thread_html）](#html生成（generate_thread_html）)
  - [まとめ](#まとめ)
- [05 - 全文検索（search.py）](#05---全文検索（searchpy）)
  - [このファイルの役割](#このファイルの役割)
  - [全体の流れ](#全体の流れ)
  - [キーワードの分類](#キーワードの分類)
  - [FTS5検索（3文字以上のキーワードがある場合）](#fts5検索（3文字以上のキーワードがある場合）)
  - [LIKEのみの検索（全て2文字以下の場合）](#likeのみの検索（全て2文字以下の場合）)
  - [ソートの切り替え](#ソートの切り替え)
  - [パラメータの渡し方](#パラメータの渡し方)
  - [検索結果の表示](#検索結果の表示)
  - [まとめ](#まとめ)
- [06 - スレッド一覧とソート（index.py）](#06---スレッド一覧とソート（indexpy）)
  - [このファイルの役割](#このファイルの役割)
  - [全体の流れ](#全体の流れ)
  - [SortType の定義](#sorttype-の定義)
  - [ソート条件の組み立て](#ソート条件の組み立て)
  - [スレッド一覧のクエリ](#スレッド一覧のクエリ)
  - [ページネーションの表示ロジック](#ページネーションの表示ロジック)
  - [last_post_at のフォールバック](#last_post_at-のフォールバック)
  - [まとめ](#まとめ)

---

## 技術スタック

```
FastAPI      Webフレームワーク（Python）
SQLite       データベース（FTS5全文検索を使用）
uvicorn      ASGIサーバー
Pydantic     リクエストの型チェック
```

---

## ファイル構成

```
app.py          起動ファイル・ルーター統合
config.py       定数（APIキー・ページ件数）
auth.py         APIキー認証
ascii_art.py    アスキーアート
init_db.py      DB初期化
webhook.py      Webhookエンドポイント
post.py         書き込み処理
thread.py       スレッド表示
search.py       全文検索
index.py        スレッド一覧
```

---

## ページ構成

```
/              スレッド一覧（is_visible=1のみ）
/thread/{id}   スレッド表示（webhook別枠 + コメント一覧）
/search        全文検索（FTS5 trigram + LIKEハイブリッド）
/webhook/news  スレッド自動作成（APIキー認証）
```

---

## DB設計の全体像

```
threads          スレッド
  ├── webhook_posts   Webhookニュース本文（1件）
  ├── user_posts      ユーザーコメント（複数）
  │     └── votes     up/down評価
  └── posts_fts       全文検索インデックス（仮想テーブル）
```

---

## app.py（起動ファイル）

各機能は独立したファイルに分かれており、`app.py`で一本に組み上げます。

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

from init_db import init_db
import index, webhook, thread, post, search

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # 起動時にDBを初期化
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(index.router)
app.include_router(webhook.router)
app.include_router(thread.router)
app.include_router(post.router)
app.include_router(search.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
```

`lifespan`はFastAPIの起動・終了時の処理を定義する仕組みです。`yield`の前が起動時、後が終了時の処理です。ここでは起動時に`init_db()`を呼んでDBを準備しています。

`include_router`で各ファイルのルーターを登録します。各ファイルは`APIRouter()`を使って独立したルートを定義しており、`app.py`はそれを束ねるだけです。

---


---

# 01 - データベースの設計と初期化（init_db.py）

## このファイルの役割

アプリが起動するときに一番最初に呼ばれる関数 `init_db()` を定義しています。
SQLiteのデータベースファイル（`bbs.db`）を作成し、必要なテーブルをすべて準備します。

---

## テーブル構成の全体像

この掲示板は4つのテーブルと1つの全文検索用仮想テーブルで構成されています。

```
threads          スレッド（話題のまとまり）
webhook_posts    Webhookで投稿されたニュース本文（スレッドに1件）
user_posts       ユーザーが書き込んだコメント（スレッドに複数）
votes            user_postsへのup/down評価
posts_fts        全文検索用インデックス（仮想テーブル）
```

テーブルの関係はこうなっています。

```
threads
  └── webhook_posts（thread_idで紐づく、1件）
  └── user_posts（thread_idで紐づく、複数）
        └── votes（post_idで紐づく）
```

---

## 外部キー制約の有効化

```python
conn.execute("PRAGMA foreign_keys = ON")
```

SQLiteはデフォルトで外部キー制約が**無効**になっています。これを有効にしないと`ON DELETE CASCADE`が機能しません。つまりスレッドを削除しても`webhook_posts`や`user_posts`が残ったままになります。

DBに接続するすべてのファイルの`with sqlite3.connect('bbs.db') as conn:`の直後に必ず書く必要があります。

---

## 各テーブルの詳細

### threads（スレッド）

```python
conn.execute('''
    CREATE TABLE IF NOT EXISTS threads (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        title        TEXT NOT NULL,
        created_at   TEXT NOT NULL,
        last_post_at TEXT,
        views        INTEGER DEFAULT 0,
        is_visible   INTEGER DEFAULT 1,
        status       TEXT DEFAULT 'public'
    )
''')
```

| カラム | 説明 |
|--------|------|
| `id` | スレッドの一意なID。自動採番 |
| `title` | スレッドのタイトル |
| `created_at` | スレッド作成日時 |
| `last_post_at` | 最後にコメントされた日時。更新順ソートに使う |
| `views` | 閲覧数。スレッドページを開くたびに+1 |
| `is_visible` | 表示フラグ。`1`=表示、`0`=非表示 |
| `status` | 管理用の状態。`public` / `hidden_temp` / `hidden_perm` / `spam` |

`is_visible`と`status`の使い分けは次の通りです。

```
is_visible → 表示・非表示の高速判定に使う（WHERE is_visible = 1）
status     → 管理者が非表示にした理由や状態を把握するために使う

連動ルール
  status = 'public'      → is_visible = 1
  status = 'hidden_temp' → is_visible = 0（一時非表示、戻す予定あり）
  status = 'hidden_perm' → is_visible = 0（恒久非表示、削除候補）
  status = 'spam'        → is_visible = 0（スパム判定）
```

---

### webhook_posts（Webhookニュース本文）

```python
conn.execute('''
    CREATE TABLE IF NOT EXISTS webhook_posts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id  INTEGER NOT NULL,
        author     TEXT DEFAULT 'ニュースBot',
        body       TEXT NOT NULL,
        source_url TEXT,
        created_at TEXT NOT NULL,
        is_visible INTEGER DEFAULT 1,
        status     TEXT DEFAULT 'public',
        FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
    )
''')
```

外部スクリプトからWebhookでスレッドを作成したときの本文が入ります。
1スレッドにつき1件だけ存在します。スレッドページでは別枠として表示され、コメントのレス番号には含まれません。

`FOREIGN KEY ... ON DELETE CASCADE` は、親のスレッド（threads）が削除されたとき、このテーブルの関連レコードも自動で削除される設定です。

物理削除すると連鎖的に全データが消えるため、管理者画面では`status`を変更する論理削除をデフォルトにします。物理削除は別途確認を必要とする操作として扱います。

---

### user_posts（ユーザーコメント）

```python
conn.execute('''
    CREATE TABLE IF NOT EXISTS user_posts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id  INTEGER NOT NULL,
        name       TEXT DEFAULT 'anonymous',
        content    TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_visible INTEGER DEFAULT 1,
        status     TEXT DEFAULT 'public',
        FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
    )
''')
```

ユーザーがフォームから書き込んだコメントが入ります。
レス番号はこのテーブルの件数をもとに計算されます。

---

### votes（評価）

```python
conn.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id   INTEGER NOT NULL,
        vote_type TEXT NOT NULL CHECK (vote_type IN ('up', 'down')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (post_id) REFERENCES user_posts (id) ON DELETE CASCADE
    )
''')
```

`user_posts`の各コメントへのup/down評価を記録します。
`CHECK (vote_type IN ('up', 'down'))` で、想定外の値が入らないようにSQLite側で制約をかけています。

将来ログイン機能を追加したときは、`user_id`カラムを追加するだけで「一人一票」の制限が実現できる設計です。

---

## FTS5 全文検索テーブル（posts_fts）

FTS5（Full Text Search 5）はSQLiteに組み込まれた全文検索エンジンです。
通常の`LIKE`検索とは異なり、専用のインデックスを使って高速に検索できます。

```python
conn.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
        content,
        source_type,
        post_id UNINDEXED,
        thread_title,
        author_name,
        tokenize='trigram'
    )
''')
```

### VIRTUAL TABLEとは

通常のテーブルとは異なり、実データを持たずインデックス情報だけを管理する特殊なテーブルです。`USING fts5` でFTS5エンジンを使うことを指定します。

### tokenize='trigram' とは

テキストを3文字ずつ区切ってインデックスを作る方式です。日本語は英語と違って単語の境界（スペース）がないため、英語向けの`porter`などのtokenizerでは日本語の検索ができません。trigramは文字単位で区切るため日本語に適しています。

```
例：「東京で大雪」をtrigramで分割すると
→「東京で」「京で大」「で大雪」という3文字の組み合わせでインデックス化
→「東京で」を含む検索でヒットする
```

ただしtrigramは3文字以上のキーワードにしか対応できません。2文字以下のキーワードは`LIKE`検索にフォールバックします（`search.py`で処理）。

### UNINDEXED とは

`post_id UNINDEXED` はこのカラムを検索対象にしないという指定です。`post_id`は検索には使わず、結果からもとのレコードを特定するためだけに使うので、インデックス化する必要がありません。

UNINDEXEDカラムの使い方には注意点があります。

```sql
-- ✅ JOINには使える（もとのレコードを特定する）
SELECT p.*
FROM posts_fts fts
JOIN user_posts p ON p.id = fts.post_id

-- ⚠️ WHERE検索には使えない（インデックスが効かずフルスキャンになる）
SELECT * FROM posts_fts WHERE post_id = 123
```

### 動作環境について

`tokenize='trigram'`はSQLite 3.40.0以降が必要です。起動前に確認できます。

```python
import sqlite3
conn = sqlite3.connect(':memory:')
try:
    conn.execute("CREATE VIRTUAL TABLE t USING fts5(a, tokenize='trigram')")
    print("✅ trigram 利用可能")
except sqlite3.OperationalError as e:
    print(f"❌ trigram 非対応: {e}")
```

---

## トリガー

トリガーとは、テーブルへのINSERT/UPDATE/DELETEをきっかけに自動で別の処理を実行する仕組みです。

### statusとis_visibleの同期

```python
for table in ['threads', 'webhook_posts', 'user_posts']:
    conn.execute(f'''
        CREATE TRIGGER {table}_status_sync
        AFTER UPDATE OF status ON {table}
        BEGIN
            UPDATE {table}
            SET is_visible = CASE
                WHEN NEW.status = 'public' THEN 1
                ELSE 0
            END
            WHERE id = NEW.id;
        END
    ''')
```

管理者が`status`を変更したとき、`is_visible`が自動で連動します。アプリケーション側でこの同期を書く必要はありません。

```
status = 'public'      → is_visible が自動で 1 になる
status = 'hidden_temp' → is_visible が自動で 0 になる
status = 'hidden_perm' → is_visible が自動で 0 になる
status = 'spam'        → is_visible が自動で 0 になる
```

3つのテーブル（threads / webhook_posts / user_posts）すべてに同じトリガーを作成しています。

---

### user_postsへのINSERT時

```python
conn.execute('''
    CREATE TRIGGER user_posts_after_insert
    AFTER INSERT ON user_posts
    BEGIN
        INSERT INTO posts_fts(content, source_type, post_id, thread_title, author_name)
        SELECT
            NEW.content,
            'user',
            NEW.id,
            t.title,
            NEW.name
        FROM threads t
        WHERE t.id = NEW.thread_id;

        UPDATE threads
        SET last_post_at = NEW.created_at
        WHERE id = NEW.thread_id;
    END
''')
```

`NEW` は今INSERTされたばかりのレコードを指します。
このトリガーは2つのことを自動でやります。

```
1. posts_fts にコメント内容を登録（全文検索インデックスを更新）
2. threads の last_post_at を最新の投稿日時に更新
```

### webhook_postsへのINSERT時

```python
conn.execute('''
    CREATE TRIGGER webhook_posts_after_insert
    AFTER INSERT ON webhook_posts
    BEGIN
        INSERT INTO posts_fts(content, source_type, post_id, thread_title, author_name)
        SELECT
            NEW.body,
            'webhook',
            NEW.id,
            t.title,
            NEW.author
        FROM threads t
        WHERE t.id = NEW.thread_id;
    END
''')
```

Webhookのニュース本文も全文検索の対象にします。`source_type='webhook'`として登録することで、検索結果からWebhookの投稿かユーザーの投稿かを区別できます。

---

## インデックス

インデックスは特定のカラムへの検索・ソートを高速化するための仕組みです。

```python
conn.execute('CREATE INDEX IF NOT EXISTS idx_user_posts_thread_id ON user_posts(thread_id)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_webhook_posts_thread_id ON webhook_posts(thread_id)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_last_post ON threads(last_post_at)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_views ON threads(views)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_user_posts_visible ON user_posts(is_visible)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_visible ON threads(is_visible)')
```

| インデックス | 高速化される操作 |
|---|---|
| `idx_user_posts_thread_id` | スレッドのコメント一覧取得 |
| `idx_webhook_posts_thread_id` | スレッドのニュース本文取得 |
| `idx_threads_created_at` | 作成日時順ソート |
| `idx_threads_last_post` | 更新順ソート |
| `idx_threads_views` | 閲覧数順ソート |
| `idx_user_posts_visible` | 表示中コメントの絞り込み |
| `idx_threads_visible` | 表示中スレッドの絞り込み |

---

## CREATE TABLE IF NOT EXISTS について

`IF NOT EXISTS` をつけることで、テーブルがすでに存在している場合はエラーにならずスキップします。アプリを再起動するたびに`init_db()`が呼ばれますが、既存のデータが消えることはありません。

---

## まとめ

```
init_db() がやっていること

1. threads テーブル作成
2. webhook_posts テーブル作成
3. user_posts テーブル作成
4. votes テーブル作成
5. posts_fts 仮想テーブル作成（FTS5 trigram）
6. トリガー作成（INSERT時にFTS5を自動更新）
7. インデックス作成（検索・ソートの高速化）
```


---

# 02 - Webhookでスレッドを作成する（webhook.py）

## このファイルの役割

外部スクリプトからHTTPリクエストを受け取り、ニュース記事をもとにスレッドを自動作成するエンドポイントを定義しています。

---

## 全体の流れ

```
外部スクリプト
    │
    │ POST /webhook/news
    │ Header: X-API-Key: xxxx
    │ Body: { title, body, source_url, author }
    ▼
APIキー認証
    │
    ├── 認証失敗 → 403 エラーを返す
    │
    ▼
重複チェック（1時間以内に同じタイトルがあるか）
    │
    ├── 重複あり → duplicate を返して終了
    │
    ▼
threadsテーブルにINSERT
    │
    ▼
webhook_postsテーブルにINSERT
    │  ↓ トリガー自動発火
    │  posts_fts にも自動登録（全文検索対象になる）
    │
    ▼
{ status: "ok", thread_id, url } を返す
```

---

## APIキー認証

```python
from fastapi import APIRouter, HTTPException, Depends
from auth import verify_api_key

@router.post("/webhook/news")
async def create_thread_from_news(
    news: NewsWebhook,
    api_key: str = Depends(verify_api_key)  # ← 認証
):
```

### Depends とは

FastAPIの依存性注入の仕組みです。`Depends(verify_api_key)` と書くと、このエンドポイントが呼ばれるたびに、処理の前に自動で`verify_api_key`関数を実行してくれます。

```python
# auth.py のイメージ
def verify_api_key(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key
```

リクエストヘッダーの`X-API-Key`が正しくなければ403エラーを返します。認証が通ったときだけ、その下の処理が実行されます。

`secrets.compare_digest` は文字列を比較する標準ライブラリの関数です。通常の`==`比較ではなくこれを使う理由は、タイミング攻撃（処理時間の差を測ることでAPIキーを推測する攻撃）を防ぐためです。

---

## リクエストの形式（Pydanticモデル）

```python
from pydantic import BaseModel
from typing import Optional

class NewsWebhook(BaseModel):
    title: str
    body: str
    source_url: Optional[str] = None
    author: Optional[str] = "ニュースBot"
```

### BaseModel とは

PydanticのBaseModelを継承したクラスで、リクエストのJSONを受け取る形式を定義します。FastAPIはこのモデルをもとに、リクエストボディの型チェックとパースを自動でやってくれます。

```json
// 外部スクリプトが送るJSONの例
{
    "title": "東京で大雪、交通マヒ",
    "body": "東京都内では今日から大雪が降り始め...",
    "source_url": "https://news.example.com/tokyo-snow",
    "author": "ニュースBot"
}
```

`Optional[str] = None` は省略可能なフィールドです。`source_url`と`author`は送らなくても動きます。

---

## 重複チェック

```python
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
```

同じニュースが1時間以内にすでにスレッドになっていれば、新しいスレッドを作らずに既存のスレッドIDを返します。

`datetime("now", "-1 hour")` はSQLiteの組み込み関数で、現在時刻から1時間前の日時を返します。外部スクリプトが同じニュースを誤って何度も送ってしまうケースへの対策です。

クエリの`?`はプレースホルダーです。SQLインジェクションを防ぐため、文字列を直接クエリに埋め込むのではなく、必ずこの形式を使います。

---

## DBへの書き込み

```python
# threadsテーブルにINSERT
cur = conn.execute(
    '''INSERT INTO threads (title, created_at, last_post_at, views, is_visible, status)
       VALUES (?, ?, ?, 0, 1, 'public')''',
    (news.title, now, now)
)
thread_id = cur.lastrowid

# webhook_postsテーブルにINSERT
conn.execute(
    '''INSERT INTO webhook_posts (thread_id, author, body, source_url, created_at, is_visible, status)
       VALUES (?, ?, ?, ?, ?, 1, 'public')''',
    (thread_id, news.author, news.body, news.source_url, now)
)
```

2つのテーブルに分けてデータを記録しています。

```
threads         → スレッドのタイトルと管理情報
webhook_posts   → ニュースの本文・著者・出典URL
```

`cur.lastrowid` は直前のINSERTで採番されたIDを取得します。`webhook_posts`に`thread_id`として渡すために使っています。

`with sqlite3.connect('bbs.db') as conn:` のブロックを抜けると、自動でコミット（変更の確定）またはロールバック（エラー時の取り消し）が行われます。途中でエラーが起きても中途半端なデータが残りません。

### webhook_postsへのINSERT後にトリガーが自動発火

`init_db.py`で定義したトリガーにより、`webhook_posts`にINSERTした瞬間に`posts_fts`（全文検索インデックス）への登録も自動で行われます。アプリ側で明示的に書く必要はありません。

```
webhook_posts にINSERT
    ↓ トリガー自動発火（webhook_posts_after_insert）
posts_fts にも自動でINSERT
    → 全文検索の対象になる
```

---

## レスポンス

```python
return {
    "status": "ok",
    "thread_id": thread_id,
    "title": news.title,
    "url": f"/thread/{thread_id}"
}
```

成功時は作成されたスレッドのIDとURLを返します。外部スクリプトはこのURLを使ってスレッドへのリンクを生成できます。

重複時は別のレスポンスを返します：

```python
return {
    "status": "duplicate",
    "thread_id": recent[0],
    "message": "最近同じニュースのスレッドが作成されています"
}
```

---

## 確認用エンドポイント

```python
@router.get("/webhook/test")
async def test_webhook():
    return {"message": "Webhookエンドポイントが動作しています"}

@router.get("/webhook/check-key")
async def check_api_key(api_key: str = Depends(verify_api_key)):
    return {"message": "API key is valid!"}
```

`/webhook/test` はAPIキー不要で、サーバーが動いているかだけ確認できます。
`/webhook/check-key` はAPIキーが正しいかどうかを確認できます。外部スクリプトの開発時に便利です。

---

## APIRouterとは

```python
router = APIRouter()

@router.post("/webhook/news")
...
```

FastAPIでは`app`に直接ルートを定義するのではなく、`APIRouter`を使って機能ごとにルートをまとめることができます。`app.py`でこのルーターをインクルードして一つに組み上げます。

```python
# app.py でのインクルードイメージ
from webhook import router as webhook_router
app.include_router(webhook_router)
```

---

## 外部スクリプトからの呼び出し例

```python
import requests

response = requests.post(
    "http://localhost:8000/webhook/news",
    headers={"X-API-Key": "your-api-key"},
    json={
        "title": "東京で大雪、交通マヒ",
        "body": "東京都内では今日から大雪が降り始め...",
        "source_url": "https://news.example.com/tokyo-snow"
    }
)
print(response.json())
# → {"status": "ok", "thread_id": 1, "url": "/thread/1", ...}
```

---

## まとめ

```
webhook.py がやっていること

1. POST /webhook/news でリクエストを受け取る
2. APIキー認証（Depends + verify_api_key）
3. Pydanticモデルでリクエストの型チェック
4. 重複チェック（1時間以内の同一タイトル）
5. threads にINSERT（スレッド作成）
6. webhook_posts にINSERT（本文記録）
   → トリガーで posts_fts にも自動登録
7. 結果を返す（thread_id / url）
```


---

# 03 - ユーザーの書き込み処理（post.py）

## このファイルの役割

スレッドページのフォームから送信されたコメントを受け取り、`user_posts`テーブルに保存するエンドポイントを定義しています。

---

## 全体の流れ

```
ユーザーがフォームに入力して「書き込む」ボタンを押す
    │
    │ POST /thread/{thread_id}/post
    │ Body: name=anonymous&content=コメント本文
    ▼
内容の空チェック
    │
    ├── 空 → 400エラー
    │
    ▼
スレッドの存在確認（is_visible=1のみ）
    │
    ├── 存在しない → 404エラー
    │
    ▼
user_postsにINSERT
    │  ↓ トリガー自動発火
    │  posts_fts に自動登録（全文検索対象）
    │  threads.last_post_at を自動更新
    │
    ▼
書き込み後の最終ページにリダイレクト
```

---

## エンドポイントの定義

```python
@router.post("/thread/{thread_id}/post")
async def add_post(
    thread_id: int,
    name: str = Form("anonymous"),
    content: str = Form(...)
):
```

### パスパラメータ

`/thread/{thread_id}/post` の `{thread_id}` はURLの一部として渡されます。FastAPIが自動で`int`型に変換してくれます。

```
/thread/1/post  → thread_id = 1
/thread/42/post → thread_id = 42
```

### Form() とは

HTMLフォームから送信されるデータを受け取るための指定です。`application/x-www-form-urlencoded`形式（フォームのデフォルト送信形式）を処理します。JSONとは異なります。

```python
name: str = Form("anonymous")  # デフォルト値あり、省略可能
content: str = Form(...)        # ... は必須であることを意味する
```

対応するHTMLフォームはこの形式です：

```html
<form method="post" action="/thread/1/post">
    <input type="text" name="name" value="anonymous">
    <textarea name="content"></textarea>
    <button type="submit">書き込む</button>
</form>
```

---

## バリデーション

```python
if not content.strip():
    raise HTTPException(status_code=400, detail="内容を入力してください")
```

`content.strip()` で前後の空白を取り除いた後、空文字かどうかを確認します。スペースだけの投稿を防ぐためです。

`HTTPException` はFastAPIが提供するエラーレスポンス用の例外です。`status_code=400`はリクエストが不正であることを示すHTTPステータスコードです。

---

## スレッドの存在確認

```python
thread = conn.execute(
    'SELECT id FROM threads WHERE id = ? AND is_visible = 1',
    (thread_id,)
).fetchone()

if not thread:
    raise HTTPException(status_code=404, detail="Thread not found")
```

2つのことを同時に確認しています。

```
1. そのIDのスレッドが存在するか
2. is_visible = 1（表示中）のスレッドか
```

管理者によって非表示にされたスレッドへの書き込みも、ここで弾かれます。

---

## DBへの書き込み

```python
conn.execute(
    '''INSERT INTO user_posts (thread_id, name, content, created_at, is_visible, status)
       VALUES (?, ?, ?, ?, 1, 'public')''',
    (thread_id, name or "anonymous", content.strip(), now)
)
```

`name or "anonymous"` は、nameが空文字や`None`のときに`"anonymous"`を使うPythonの書き方です。フォームで名前を消して送った場合のフォールバックです。

`content.strip()` で前後の空白を取り除いてから保存します。

書き込みと同時に`init_db.py`で定義したトリガーが自動で発火します：

```
user_posts にINSERT
    ↓ トリガー自動発火（user_posts_after_insert）
    ├── posts_fts にINSERT（全文検索対象になる）
    └── threads.last_post_at を更新（更新順ソートに使われる）
```

---

## 最終ページへのリダイレクト

```python
total_posts = conn.execute(
    'SELECT COUNT(*) FROM user_posts WHERE thread_id = ? AND is_visible = 1',
    (thread_id,)
).fetchone()[0]

last_page = math.ceil(total_posts / POSTS_PER_PAGE) if total_posts > 0 else 1

return RedirectResponse(
    url=f"/thread/{thread_id}?page={last_page}#post-{total_posts}",
    status_code=303
)
```

書き込み後に自分のコメントが見えるよう、最終ページに飛ばしています。

### math.ceil とは

切り上げ計算です。20件ずつ表示する場合、45件なら3ページ目になります。

```
45 ÷ 20 = 2.25 → ceil → 3ページ
```

### #post-{total_posts} とは

URLのハッシュフラグメントです。ブラウザはページを開いた後、この`id`を持つ要素まで自動でスクロールします。スレッドページ側に `id="post-45"` という要素があることが前提です。

### status_code=303 とは

`303 See Other` はPOSTの後にリダイレクトするときに使う標準的なHTTPステータスコードです。`302`と似ていますが、`303`はリダイレクト先を必ず`GET`で取得するという意味を持ちます。これによってブラウザの「戻る→再送信」問題（フォームの二重送信）を防ぎます。

---

## POSTS_PER_PAGE とは

```python
from config import POSTS_PER_PAGE
```

`config.py`で定義された定数です。1ページあたりの表示件数を一箇所で管理するための仕組みです。ここを変えると全ページの表示件数が一括で変わります。

---

## まとめ

```
post.py がやっていること

1. POST /thread/{thread_id}/post でフォームデータを受け取る
2. 内容の空チェック（スペースのみも弾く）
3. スレッドの存在確認（非表示スレッドも弾く）
4. user_posts にINSERT
   → トリガーで posts_fts に自動登録
   → トリガーで threads.last_post_at を自動更新
5. 書き込み後の最終ページにリダイレクト（303）
```


---

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


---

# 05 - 全文検索（search.py）

## このファイルの役割

`/search?q=キーワード` にアクセスしたときの検索ページを生成します。キーワードの文字数に応じてFTS5とLIKEを使い分け、結果をスレッド単位にまとめてソート付きで表示します。

---

## 全体の流れ

```
ユーザーが /search?q=東京&sort=hits にアクセス
    │
    ▼
キーワードを3文字以上と2文字以下に分類
    │
    ├── 3文字以上あり → FTS5で検索（LIKEを追加条件として併用）
    │
    └── 全て2文字以下 → LIKEのみで検索
    │
    ▼
結果をスレッド単位にまとめて集計
    （ヒット数 / 総レス数 / ビュー数 / スニペット）
    │
    ▼
ソート順で並べてページネーション
    │
    ▼
HTMLを生成して返す
```

---

## キーワードの分類

```python
keywords = search_query.replace("　", " ").split()

long_keywords  = [k for k in keywords if len(k) >= 3]
short_keywords = [k for k in keywords if len(k) < 3]
```

まず全角スペース（`　`）を半角スペースに統一してから`.split()`で分割します。スペース区切りでAND検索ができます。

```
「東京 大雪」→ keywords = ['東京', '大雪']
  東京 → short_keywords（2文字）→ LIKEで検索
  大雪 → short_keywords（2文字）→ LIKEで検索

「交通機関 大雪」→ keywords = ['交通機関', '大雪']
  交通機関 → long_keywords（4文字）→ FTS5で検索
  大雪     → short_keywords（2文字）→ LIKEを追加条件に
```

trigramは3文字以上のキーワードにしか対応できないため、この分類が必要です。

---

## FTS5検索（3文字以上のキーワードがある場合）

### match_exprの構築

```python
match_expr = " AND ".join(f'"{k}"' for k in long_keywords)
```

FTS5の`MATCH`句に渡す検索式を作ります。

```
long_keywords = ['交通機関', 'テレワーク']
→ match_expr = '"交通機関" AND "テレワーク"'
```

キーワードを`"`で囲むのはフレーズ検索の指定です。囲まない場合は単語の順序を問わないOR的な動作になります。

### UNION ALLによる統合ビュー

```sql
JOIN (
    SELECT id AS post_id, thread_id, content FROM user_posts WHERE is_visible = 1
    UNION ALL
    SELECT id AS post_id, thread_id, body AS content FROM webhook_posts WHERE is_visible = 1
) AS snippet ON snippet.post_id = pf.post_id
```

`user_posts`と`webhook_posts`は別テーブルですが、検索のためにひとつのテーブルのように扱いたいです。`UNION ALL`で2つのSELECT結果を縦に結合し、`snippet`という仮の名前（サブクエリ）として扱っています。

`UNION`は重複を除去しますが、`UNION ALL`は重複を除去しないため高速です。2つのテーブルにIDが重複することはないので`UNION ALL`で問題ありません。

### スレッド単位での集計

```sql
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
...
GROUP BY t.id
```

`GROUP BY t.id` でスレッドIDごとにまとめています。

`COUNT(pf.post_id)` はそのスレッド内でヒットした投稿の件数です。

`total_posts` と `snippet` はサブクエリで取得しています。サブクエリとは、SQLの中に入れ子で書く別のSELECT文です。

```
メインのSELECTが各スレッドを処理するたびに
  └── total_postsサブクエリ: そのスレッドの総コメント数を数える
  └── snippetサブクエリ: そのスレッドのヒットした最初の内容を取得する
```

### 2文字以下キーワードのLIKE追加条件

```python
if short_keywords:
    clauses = []
    for k in short_keywords:
        clauses.append("(snippet.content LIKE ? OR t.title LIKE ?)")
        like_params.extend([f"%{k}%", f"%{k}%"])
    like_conditions = "AND " + " AND ".join(clauses)
```

3文字以上のキーワードはFTS5で絞り込んだ上で、2文字以下のキーワードをさらにLIKEでAND条件として追加します。

```
例: 「交通機関 電車」で検索
  → FTS5で「交通機関」を含む投稿を絞り込み
  → さらに「電車」をLIKEで追加フィルタ
  → 両方を含む投稿だけがヒット
```

---

## LIKEのみの検索（全て2文字以下の場合）

```python
clauses = []
params = []
for k in short_keywords:
    clauses.append("(up.content LIKE ? OR t.title LIKE ?)")
    params.extend([f"%{k}%", f"%{k}%"])
where_clause = " AND ".join(clauses)
```

FTS5を使わず、`UNION ALL`で統合したテーブルに対して直接LIKEで検索します。

`%東京%` の`%`はワイルドカードで「任意の文字列」を意味します。前後に`%`をつけることで部分一致検索になります。

LIKEはFTS5より遅いですが、2文字以下の短いキーワードはFTS5 trigramでは検索できないため、このフォールバックが必要です。

---

## ソートの切り替え

```python
if sort == "hits":
    order_by = "ORDER BY hit_count DESC, t.last_post_at DESC"
elif sort == "new":
    order_by = "ORDER BY t.last_post_at DESC"
elif sort == "old":
    order_by = "ORDER BY t.last_post_at ASC"
elif sort == "posts":
    order_by = "ORDER BY total_posts DESC, t.last_post_at DESC"
```

`order_by`はSQL文字列として組み立て、後でf文字列でクエリに差し込みます。

`hit_count DESC, t.last_post_at DESC` のように2つ指定しているのはタイブレーク（同率時の並び順）です。ヒット数が同じスレッドは更新日時が新しい順に並びます。

ソートの種類は4つです。

```
hits  → そのキーワードが多く含まれるスレッド順
new   → 最近コメントがあったスレッド順
old   → 古くからあるスレッド順
posts → コメントが多いスレッド順
```

ビュー数はソートには使わず表示のみです。検索結果においてはヒット数・レス数・更新日時の方が有用な並び順のためです。

---

## パラメータの渡し方

FTS5検索時のクエリ実行部分はパラメータが複数あり順序に注意が必要です：

```python
results = conn.execute(
    sql,
    [match_expr]           # snippetサブクエリのMATCH用
    + like_params          # snippet側のLIKE条件用
    + [match_expr]         # JOINのFTS5 MATCH用
    + [match_expr]         # WHERE句のFTS5 MATCH用
    + like_params          # WHERE句のLIKE条件用
    + [SEARCH_RESULTS_PER_PAGE, offset]  # LIMIT/OFFSET用
).fetchall()
```

SQLの`?`プレースホルダーは順番通りに値が対応します。クエリ内の`?`の数とリストの要素数が一致している必要があります。

`match_expr`が3回登場しているのは、同じキーワードをSQL内の3箇所で使っているためです。

```sql
-- 1回目: snippetサブクエリの中
(SELECT pf2.content FROM posts_fts pf2
 WHERE pf2.content MATCH ?       ← ここ
 LIMIT 1) as snippet

-- 2回目: JOINの条件
JOIN (...) AS snippet ON snippet.post_id = pf.post_id
WHERE pf.content MATCH ?         ← ここ

-- 3回目: WHERE句の絞り込み
WHERE pf.content MATCH ?         ← ここ
AND t.is_visible = 1
```

SQLiteの`?`はその場限りの使い捨てで、一度使った値を再利用する仕組みがありません。同じ値でも登場するたびにリストに追加する必要があります。将来リファクタリングするなら、サブクエリを整理して`match_expr`の登場回数を減らすことが改善点になります。

---

## 検索結果の表示

```python
for row in results:
    thread_id, title, last_post_at, views, hit_count, total_posts, snippet = row
    snippet_html = snippet[:100] + "..." if snippet and len(snippet) > 100 else (snippet or "")
```

各スレッドについてこの情報を表示します：

```
📌 スレッドタイトル
🔍 3件ヒット | 💬 12レス | 👁 340ビュー | 🕐 2026-04-29
「...ヒットした投稿の最初の100文字...」
```

`snippet[:100]` でスニペットを100文字に切り詰め、長い場合は`...`をつけます。

---

## まとめ

```
search.py がやっていること

1. GET /search?q=...&sort=...&page=... でリクエストを受け取る
2. キーワードを3文字以上と2文字以下に分類
3. 3文字以上あり → FTS5で検索
               2文字以下は追加のLIKE条件として併用
   全て2文字以下 → LIKEのみで検索
4. 結果をスレッド単位にまとめて集計
   （ヒット数 / 総レス数 / ビュー数 / スニペット）
5. ソート順で並べてページネーション
6. HTMLを生成して返す

検索エンジンの使い分け
  3文字以上 → FTS5 trigram（高速・インデックス検索）
  2文字以下 → LIKE（低速・全件スキャン、フォールバック）
```


---

# 06 - スレッド一覧とソート（index.py）

## このファイルの役割

`/` にアクセスしたときのトップページを生成します。表示中のスレッドをソート順・ページネーション付きで一覧表示します。

---

## 全体の流れ

```
ユーザーが /?sort=new&page=1 にアクセス
    │
    ▼
ソート条件を決定（new / old / posts / updated / views）
    │
    ▼
is_visible=1 のスレッド総数を取得
    │
    ▼
ページネーション計算
    │
    ▼
スレッド一覧を取得
（user_postsのレス数・ビュー数・最終更新も一緒に）
    │
    ▼
HTMLを生成して返す
```

---

## SortType の定義

```python
from typing import Literal

SortType = Literal["new", "old", "posts", "updated", "views"]
```

`Literal` はPythonの型ヒントで、「この変数はこれらの値のどれかしか取れない」という指定です。FastAPIはこれを使って、想定外のsortパラメータが来た場合に自動でバリデーションエラーを返します。

```
/?sort=new     → OK
/?sort=views   → OK
/?sort=invalid → 422 Unprocessable Entity（自動でエラー）
```

---

## ソート条件の組み立て

```python
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
```

ソートの種類は5つです。

```
new     → スレッドIDの降順（新しく作られたスレッドが上）
old     → スレッドIDの昇順（古いスレッドが上）
posts   → レス数の多い順（盛り上がっているスレッドが上）
updated → 最終コメント日時の新しい順（最近動きのあるスレッドが上）
views   → 閲覧数の多い順（よく見られているスレッドが上）
```

`new`と`old`は`created_at`ではなく`id`でソートしています。`id`は自動採番で必ず作成順に増えるため、`created_at`より確実な順序になります。同時に複数スレッドが作成された場合でも順序が安定します。

`posts`と`updated`と`views`は`t.id DESC`をタイブレークとして追加しています。同率のスレッドは新しいものが上になります。

---

## スレッド一覧のクエリ

```python
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
```

### LEFT JOIN とは

`LEFT JOIN`は左側のテーブル（threads）の全レコードを残しつつ、右側のテーブル（user_posts）を結合します。コメントが0件のスレッドも一覧に表示するために`LEFT JOIN`を使っています。

```
INNER JOIN → 両方に一致するものだけ残す（コメント0件のスレッドが消える）
LEFT JOIN  → 左側は全て残す（コメント0件でも表示される）
```

### JOIN条件の is_visible

```sql
LEFT JOIN user_posts p ON t.id = p.thread_id AND p.is_visible = 1
```

JOINの条件に`p.is_visible = 1`を入れています。`WHERE`句に書くのではなくJOINの`ON`に書く理由は、`WHERE`に書くと`LEFT JOIN`が事実上`INNER JOIN`になってしまうためです。

```
ON に書く   → 非表示コメントを除外した上でLEFT JOINが成立
              コメントが全て非表示のスレッドはres_count=0で表示される

WHERE に書く → 非表示コメントしかないスレッドが一覧から消える（意図しない動作）
```

### GROUP BY と COUNT

```sql
COUNT(p.id) as res_count
...
GROUP BY t.id
```

`GROUP BY t.id` でスレッドIDごとにまとめ、`COUNT(p.id)`でそのスレッドのコメント数を数えます。`COUNT(p.id)`は`p.id`が`NULL`でないものだけを数えるため、コメントが0件のスレッドは0になります。

### f文字列でのSQL組み立て

```python
threads = conn.execute(f'''
    ...
    {order_by}
    ...
''', (THREADS_PER_PAGE, offset))
```

`order_by`はf文字列で直接埋め込んでいます。これはソート条件がユーザーの入力ではなく、`SortType`で検証済みのコード内の文字列だから安全です。ユーザーの入力を直接f文字列に埋め込むとSQLインジェクションのリスクがあるため、ユーザー入力には必ず`?`プレースホルダーを使います。

---

## ページネーションの表示ロジック

```python
start_page = max(1, current_page - 5)
end_page = min(total_pages, start_page + 9)
for p in range(start_page, end_page + 1):
    if p == current_page:
        html += f'<span class="current">{p}</span>'
    else:
        html += f'<a href="/?sort={current_sort}&page={p}">{p}</a>'
```

現在のページを中心に最大10ページ分のリンクを表示します。

```
現在3ページ目（全20ページ）の場合
start_page = max(1, 3-5) = 1
end_page   = min(20, 1+9) = 10
→ 1, 2, [3], 4, 5, 6, 7, 8, 9, 10 を表示

現在15ページ目（全20ページ）の場合
start_page = max(1, 15-5) = 10
end_page   = min(20, 10+9) = 19
→ 10, 11, ..., 14, [15], 16, ..., 19 を表示
```

### ソートを維持したページリンク

```python
html += f'<a href="/?sort={current_sort}&page={p}">{p}</a>'
```

ページリンクに`sort={current_sort}`を含めることで、ページを移動してもソート順が維持されます。`sort`を含めないとページ遷移時にデフォルト（new）に戻ってしまいます。

---

## last_post_at のフォールバック

```python
📅 {created_at} | 💬 {res_count}レス | 👁 {views}ビュー | 🕐 最終更新: {last_post_at or created_at}
```

`last_post_at or created_at` は、`last_post_at`が`None`の場合に`created_at`を代わりに表示します。コメントが一度もついていないスレッドは`last_post_at`が`None`になるためです。

---

## まとめ

```
index.py がやっていること

1. GET /?sort=...&page=... でリクエストを受け取る
2. SortType で sort パラメータをバリデーション
3. ソート条件を ORDER BY 文字列として組み立て
4. is_visible=1 のスレッド総数を取得
5. ページネーション計算
6. LEFT JOIN で user_posts のレス数を集計しながらスレッド取得
7. HTMLを生成して返す

ソートの種類
  new     → 新しく作られたスレッド順（id DESC）
  old     → 古いスレッド順（id ASC）
  posts   → レス数の多い順
  updated → 最近コメントがあった順（last_post_at DESC）
  views   → よく見られている順（views DESC）
```

---
