"""
CharglyBot V3 — قاعدة البيانات الكاملة
SQLite + aiosqlite — يدعم الألعاب، الباقات، الطلبات، الإحصائيات
"""
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional

from core.config import PAYMENT_TIMEOUT_MINUTES
from core.states import S

DB_PATH = "charglybot_v3.db"


# ══════════════════════════════════════════════════
#  تهيئة الجداول
# ══════════════════════════════════════════════════

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA journal_mode=WAL;

        -- المستخدمون
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            joined_at   TEXT DEFAULT (datetime('now')),
            is_banned   INTEGER DEFAULT 0,
            last_action TEXT
        );

        -- الألعاب (قابلة للإضافة/الحذف من الأدمن)
        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            emoji       TEXT NOT NULL DEFAULT '🎮',
            is_active   INTEGER DEFAULT 1,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- الباقات (مرتبطة بالألعاب)
        CREATE TABLE IF NOT EXISTS packages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game_key    TEXT NOT NULL REFERENCES games(key),
            label       TEXT NOT NULL,
            amount      REAL NOT NULL DEFAULT 0,
            currency    TEXT NOT NULL DEFAULT 'دج',
            cost        REAL NOT NULL DEFAULT 0,
            is_active   INTEGER DEFAULT 1,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- الطلبات
        CREATE TABLE IF NOT EXISTS orders (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id               INTEGER NOT NULL REFERENCES users(id),
            game_key              TEXT NOT NULL,
            game_name             TEXT NOT NULL,
            player_id             TEXT NOT NULL,
            player_name           TEXT NOT NULL,
            screenshot_file_id    TEXT,
            package_id            INTEGER REFERENCES packages(id),
            package_label         TEXT NOT NULL,
            amount                REAL NOT NULL,
            cost                  REAL NOT NULL DEFAULT 0,
            currency              TEXT NOT NULL DEFAULT 'دج',
            status                TEXT NOT NULL DEFAULT 'awaiting_approval',
            note                  TEXT,
            proof_file_id         TEXT,
            payment_deadline      TEXT,
            created_at            TEXT DEFAULT (datetime('now')),
            updated_at            TEXT DEFAULT (datetime('now'))
        );

        -- سجل كل التغييرات على الطلبات (audit log)
        CREATE TABLE IF NOT EXISTS order_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL,
            action      TEXT NOT NULL,
            actor       TEXT NOT NULL,
            note        TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- الإشعارات الجماعية
        CREATE TABLE IF NOT EXISTS broadcasts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message     TEXT NOT NULL,
            sent_count  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_game   ON orders(game_key);
        CREATE INDEX IF NOT EXISTS idx_orders_date   ON orders(created_at);
        CREATE INDEX IF NOT EXISTS idx_pkgs_game     ON packages(game_key);
        """)

        # إضافة الألعاب الافتراضية إن لم تكن موجودة
        await db.execute("""
            INSERT OR IGNORE INTO games (key, name, emoji, sort_order)
            VALUES
              ('freefire', 'Free Fire', '🔥', 1),
              ('pubg',     'PUBG Mobile', '🎯', 2)
        """)

        # إضافة باقات Free Fire الافتراضية (فقط إن لم تكن موجودة)
        existing = await db.execute(
            "SELECT COUNT(*) FROM packages WHERE game_key='freefire'"
        )
        row = await existing.fetchone()
        if not row or row[0] == 0:
            default_packages = [
                ("💎 100 جوهرة",  120,  85,  1),
                ("💎 310 جوهرة",  350,  250, 2),
                ("💎 520 جوهرة",  580,  420, 3),
                ("💎 1060 جوهرة", 1100, 800, 4),
            ]
            for label, amount, cost, sort_order in default_packages:
                await db.execute(
                    """INSERT INTO packages
                         (game_key, label, amount, currency, cost, sort_order)
                       VALUES ('freefire', ?, ?, 'دج', ?, ?)""",
                    (label, amount, cost, sort_order)
                )

        await db.commit()


# ══════════════════════════════════════════════════
#  المستخدمون
# ══════════════════════════════════════════════════

async def upsert_user(user_id: int, username: str, full_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name
        """, (user_id, username or "", full_name or ""))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT is_banned FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row[0])


async def check_rate_limit(user_id: int, seconds: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_action FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        if not row or not row[0]:
            return True
        return datetime.utcnow() - datetime.fromisoformat(row[0]) > timedelta(seconds=seconds)


async def touch_last_action(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_action=? WHERE id=?",
                         (datetime.utcnow().isoformat(), user_id))
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users WHERE is_banned=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ══════════════════════════════════════════════════
#  الألعاب
# ══════════════════════════════════════════════════

async def get_active_games() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM games WHERE is_active=1 ORDER BY sort_order, id
        """)
        return [dict(r) for r in await cur.fetchall()]


async def get_all_games() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM games ORDER BY sort_order, id")
        return [dict(r) for r in await cur.fetchall()]


async def get_game(key: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM games WHERE key=?", (key,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def add_game(key: str, name: str, emoji: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO games (key, name, emoji) VALUES (?,?,?)",
                             (key, name, emoji))
            await db.commit()
        return True
    except Exception:
        return False


async def toggle_game(key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE games SET is_active = 1 - is_active WHERE key=?", (key,))
        await db.commit()
    return True


async def delete_game(key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM packages WHERE game_key=?", (key,))
        await db.execute("DELETE FROM games WHERE key=?", (key,))
        await db.commit()
    return True


# ══════════════════════════════════════════════════
#  الباقات
# ══════════════════════════════════════════════════

async def get_packages(game_key: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM packages
            WHERE game_key=? AND is_active=1
            ORDER BY sort_order, amount
        """, (game_key,))
        return [dict(r) for r in await cur.fetchall()]


async def get_all_packages(game_key: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM packages WHERE game_key=?
            ORDER BY sort_order, amount
        """, (game_key,))
        return [dict(r) for r in await cur.fetchall()]


async def get_package(pkg_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM packages WHERE id=?", (pkg_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def add_package(game_key: str, label: str, amount: float,
                       currency: str, cost: float) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO packages (game_key, label, amount, currency, cost)
            VALUES (?,?,?,?,?)
        """, (game_key, label, amount, currency, cost))
        await db.commit()
        return cur.lastrowid


async def update_package_price(pkg_id: int, amount: float, cost: float) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE packages SET amount=?, cost=? WHERE id=?",
                         (amount, cost, pkg_id))
        await db.commit()
    return True


async def toggle_package(pkg_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE packages SET is_active = 1 - is_active WHERE id=?",
                         (pkg_id,))
        await db.commit()
    return True


async def delete_package(pkg_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM packages WHERE id=?", (pkg_id,))
        await db.commit()
    return True


# ══════════════════════════════════════════════════
#  الطلبات
# ══════════════════════════════════════════════════

async def count_active_orders(user_id: int) -> int:
    placeholders = ",".join(f"'{s}'" for s in S.ACTIVE)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            f"SELECT COUNT(*) FROM orders WHERE user_id=? AND status IN ({placeholders})",
            (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def create_order(
    user_id: int, game_key: str, game_name: str,
    player_id: str, player_name: str, screenshot_file_id: str,
    package_id: int, package_label: str,
    amount: float, cost: float, currency: str,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO orders
              (user_id, game_key, game_name, player_id, player_name,
               screenshot_file_id, package_id, package_label,
               amount, cost, currency, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'awaiting_approval')
        """, (user_id, game_key, game_name, player_id, player_name,
              screenshot_file_id, package_id, package_label,
              amount, cost, currency))
        await db.commit()
        order_id = cur.lastrowid

    await log_action(order_id, "CREATED", f"user:{user_id}")
    return order_id


async def get_order(order_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT o.*, u.username, u.full_name
            FROM orders o LEFT JOIN users u ON o.user_id=u.id
            WHERE o.id=?
        """, (order_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_user_active_order(user_id: int) -> Optional[dict]:
    """الطلب النشط الحالي للمستخدم"""
    placeholders = ",".join(f"'{s}'" for s in S.ACTIVE)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"SELECT * FROM orders WHERE user_id=? AND status IN ({placeholders}) ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_order_field(order_id: int, field: str, value: str, actor: str = "user") -> bool:
    """تعديل حقل في الطلب — يُمنع إذا كان الطلب محمياً"""
    order = await get_order(order_id)
    if not order or order["status"] not in S.EDITABLE:
        return False
    allowed = {"player_id", "player_name", "screenshot_file_id", "package_id",
               "package_label", "amount", "cost", "game_key", "game_name"}
    if field not in allowed:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE orders SET {field}=?, updated_at=? WHERE id=?",
            (value, datetime.utcnow().isoformat(), order_id)
        )
        await db.commit()
    await log_action(order_id, f"EDIT:{field.upper()}", actor)
    return True


async def set_order_status(order_id: int, status: str,
                            note: str = "", actor: str = "system") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status=?, note=?, updated_at=? WHERE id=?
        """, (status, note, datetime.utcnow().isoformat(), order_id))
        await db.commit()
    await log_action(order_id, f"STATUS:{status.upper()}", actor, note)
    return True


async def approve_order(order_id: int) -> bool:
    deadline = (datetime.utcnow() + timedelta(
        minutes=PAYMENT_TIMEOUT_MINUTES)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status='waiting_payment', payment_deadline=?, updated_at=?
            WHERE id=?
        """, (deadline, datetime.utcnow().isoformat(), order_id))
        await db.commit()
    await log_action(order_id, "APPROVED", "admin")
    return True


async def set_payment_proof(order_id: int, file_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders
            SET proof_file_id=?, status='payment_sent', updated_at=?
            WHERE id=?
        """, (file_id, datetime.utcnow().isoformat(), order_id))
        await db.commit()
    await log_action(order_id, "PROOF_SUBMITTED", "user")
    return True


async def get_user_orders(user_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM orders WHERE user_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        return [dict(r) for r in await cur.fetchall()]


async def get_all_orders(status: Optional[str] = None, limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute("""
                SELECT o.*, u.username, u.full_name
                FROM orders o LEFT JOIN users u ON o.user_id=u.id
                WHERE o.status=?
                ORDER BY o.created_at DESC LIMIT ?
            """, (status, limit))
        else:
            cur = await db.execute("""
                SELECT o.*, u.username, u.full_name
                FROM orders o LEFT JOIN users u ON o.user_id=u.id
                ORDER BY o.created_at DESC LIMIT ?
            """, (limit,))
        return [dict(r) for r in await cur.fetchall()]


async def get_expired_orders() -> list[dict]:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM orders
            WHERE status='waiting_payment'
              AND payment_deadline IS NOT NULL
              AND payment_deadline < ?
        """, (now,))
        return [dict(r) for r in await cur.fetchall()]


async def cancel_order(order_id: int, user_id: int) -> bool:
    """العميل يلغي طلبه — مسموح فقط في EDITABLE"""
    order = await get_order(order_id)
    if not order or order["user_id"] != user_id:
        return False
    if order["status"] not in S.EDITABLE:
        return False
    await set_order_status(order_id, S.CANCELLED, actor=f"user:{user_id}")
    return True


# ══════════════════════════════════════════════════
#  Audit Log
# ══════════════════════════════════════════════════

async def log_action(order_id: int, action: str, actor: str, note: str = "") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO order_logs (order_id, action, actor, note)
            VALUES (?,?,?,?)
        """, (order_id, action, actor, note or ""))
        await db.commit()


async def get_order_logs(order_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM order_logs WHERE order_id=? ORDER BY created_at
        """, (order_id,))
        return [dict(r) for r in await cur.fetchall()]


# ══════════════════════════════════════════════════
#  الإحصائيات
# ══════════════════════════════════════════════════

async def daily_stats() -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:

        async def sc(q, *p):
            cur = await db.execute(q, p)
            r = await cur.fetchone()
            return r[0] if r else 0

        total     = await sc("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", f"{today}%")
        pending   = await sc("SELECT COUNT(*) FROM orders WHERE status='awaiting_approval'")
        waiting   = await sc("SELECT COUNT(*) FROM orders WHERE status='waiting_payment_confirm'")
        processing= await sc("SELECT COUNT(*) FROM orders WHERE status='processing'")
        completed = await sc("SELECT COUNT(*) FROM orders WHERE status='completed' AND created_at LIKE ?", f"{today}%")
        rejected  = await sc("SELECT COUNT(*) FROM orders WHERE status='rejected'  AND created_at LIKE ?", f"{today}%")
        expired   = await sc("SELECT COUNT(*) FROM orders WHERE status='expired'   AND created_at LIKE ?", f"{today}%")
        revenue   = await sc("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='completed' AND created_at LIKE ?", f"{today}%")
        profit    = await sc("SELECT COALESCE(SUM(amount-cost),0) FROM orders WHERE status='completed' AND created_at LIKE ?", f"{today}%")
        all_time  = await sc("SELECT COUNT(*) FROM orders")
        users     = await sc("SELECT COUNT(*) FROM users")

        # أكثر لعبة مبيعاً
        cur = await db.execute("""
            SELECT game_name, COUNT(*) as cnt FROM orders
            WHERE status='completed' AND created_at LIKE ?
            GROUP BY game_key ORDER BY cnt DESC LIMIT 1
        """, (f"{today}%",))
        top_game_row = await cur.fetchone()
        top_game = top_game_row[0] if top_game_row else "—"

        # أكثر باقة مبيعاً
        cur = await db.execute("""
            SELECT package_label, COUNT(*) as cnt FROM orders
            WHERE status='completed' AND created_at LIKE ?
            GROUP BY package_label ORDER BY cnt DESC LIMIT 1
        """, (f"{today}%",))
        top_pkg_row = await cur.fetchone()
        top_pkg = top_pkg_row[0] if top_pkg_row else "—"

        # إحصائيات الأسبوع
        week_start = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        w_revenue = await sc("""
            SELECT COALESCE(SUM(amount),0) FROM orders
            WHERE status='completed' AND created_at >= ?
        """, f"{week_start}")
        w_profit = await sc("""
            SELECT COALESCE(SUM(amount-cost),0) FROM orders
            WHERE status='completed' AND created_at >= ?
        """, f"{week_start}")

    rate = round(completed / total * 100) if total else 0
    return dict(
        total=total, pending=pending, waiting=waiting,
        processing=processing, completed=completed,
        rejected=rejected, expired=expired,
        revenue=revenue, profit=profit,
        w_revenue=w_revenue, w_profit=w_profit,
        rate=rate, top_game=top_game, top_pkg=top_pkg,
        all_time=all_time, users=users,
    )
