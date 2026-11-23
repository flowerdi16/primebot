import aiosqlite

DB_PATH = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                section_id INTEGER NOT NULL,
                answer TEXT NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, section_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS forwarded_messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY(chat_id, message_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL
            )
        """)
        await db.commit()


async def save_user(user):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (user.id, user.username, user.full_name))
        await db.commit()


async def get_completed(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT section_id FROM votes WHERE user_id = ?", (user_id,)
        ) as cursor:
            return {row[0] for row in await cursor.fetchall()}


async def save_vote(user, section_id, answer):
    # INSERT OR IGNORE + UNIQUE исключают повтор даже при одновременных запросах.
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO votes
                (user_id, section_id, answer, username, full_name)
            VALUES (?, ?, ?, ?, ?)
        """, (user.id, section_id, answer, user.username, user.full_name))
        await db.commit()
        return cursor.rowcount == 1


async def remember_forward(chat_id, message_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO forwarded_messages
                (chat_id, message_id, user_id)
            VALUES (?, ?, ?)
        """, (chat_id, message_id, user_id))
        await db.commit()


async def get_forward_user(chat_id, message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id FROM forwarded_messages
            WHERE chat_id = ? AND message_id = ?
        """, (chat_id, message_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_votes(section_id, offset, limit):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT v.user_id, v.answer,
                   COALESCE(u.username, v.username) AS username,
                   COALESCE(u.full_name, v.full_name) AS full_name
            FROM votes v
            LEFT JOIN users u ON u.user_id = v.user_id
            WHERE v.section_id = ?
            ORDER BY v.id ASC
            LIMIT ? OFFSET ?
        """, (section_id, limit, offset)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def count_votes(section_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM votes WHERE section_id = ?", (section_id,)
        ) as cursor:
            return (await cursor.fetchone())[0]
