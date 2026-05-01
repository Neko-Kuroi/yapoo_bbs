import sqlite3
from db import get_db

def init_db():
    with get_db() as conn:

        # ========== threads ==========
        conn.execute('''
            CREATE TABLE IF NOT EXISTS threads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                last_post_at TEXT,
                views       INTEGER DEFAULT 0,
                is_visible  INTEGER DEFAULT 1,
                status      TEXT DEFAULT 'public'
            )
        ''')

        # ========== webhook_posts ==========
        conn.execute('''
            CREATE TABLE IF NOT EXISTS webhook_posts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id   INTEGER NOT NULL,
                author      TEXT DEFAULT 'ニュースBot',
                body        TEXT NOT NULL,
                source_url  TEXT,
                created_at  TEXT NOT NULL,
                is_visible  INTEGER DEFAULT 1,
                status      TEXT DEFAULT 'public',
                FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
            )
        ''')

        # ========== user_posts ==========
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_posts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id   INTEGER NOT NULL,
                name        TEXT DEFAULT 'anonymous',
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                is_visible  INTEGER DEFAULT 1,
                status      TEXT DEFAULT 'public',
                FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
            )
        ''')

        # ========== votes ==========
        conn.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id     INTEGER NOT NULL,
                vote_type   TEXT NOT NULL CHECK (vote_type IN ('up', 'down')),
                created_at  TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES user_posts (id) ON DELETE CASCADE
            )
        ''')

        # ========== FTS5 全文検索 ==========
        # trigram: 3文字単位で分割、日本語部分一致に対応
        # 2文字以下のキーワードはLIKEフォールバックで対応（検索エンドポイント側で処理）
        try:
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
            print("✅ FTS5 trigram テーブル作成成功")
        except sqlite3.OperationalError as e:
            print(f"⚠️ FTS5非対応: {e}")

        # ========== トリガー ==========

        # status変更時にis_visibleを自動同期
        try:
            for table in ['threads', 'webhook_posts', 'user_posts']:
                conn.execute(f'DROP TRIGGER IF EXISTS {table}_status_sync')
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
            print("✅ status同期トリガー作成成功")
        except sqlite3.OperationalError as e:
            print(f"⚠️ status同期トリガー作成スキップ: {e}")

        # user_posts INSERT時
        try:
            conn.execute('DROP TRIGGER IF EXISTS user_posts_after_insert')
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
            print("✅ user_posts トリガー作成成功")
        except sqlite3.OperationalError as e:
            print(f"⚠️ user_posts トリガー作成スキップ: {e}")

        # webhook_posts INSERT時
        try:
            conn.execute('DROP TRIGGER IF EXISTS webhook_posts_after_insert')
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
            print("✅ webhook_posts トリガー作成成功")
        except sqlite3.OperationalError as e:
            print(f"⚠️ webhook_posts トリガー作成スキップ: {e}")

        # ========== インデックス ==========
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_posts_thread_id ON user_posts(thread_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_webhook_posts_thread_id ON webhook_posts(thread_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_last_post ON threads(last_post_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_views ON threads(views)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_posts_visible ON user_posts(is_visible)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_threads_visible ON threads(is_visible)')
            print("✅ インデックス作成完了")
        except sqlite3.OperationalError as e:
            print(f"⚠️ 一部インデックス作成スキップ: {e}")

        print("✅ データベース初期化完了")


if __name__ == "__main__":
    init_db()