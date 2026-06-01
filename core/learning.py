"""
Learning Memory: Mengelola SQLite database untuk trade history dan self-reflection.
- trade_history: catat semua trade
- learning_memory: catat lesson learned dari AI
"""
import sqlite3
from datetime import datetime, date
from typing import Dict, Any, List, Optional


class LearningMemory:
    def __init__(self, db_path: str = "db/sqlite.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Buat tabel jika belum ada (WAL mode enabled)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()

        # trade_history
        c.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                ticket INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                close_price REAL,
                profit REAL NOT NULL,
                open_time DATETIME NOT NULL,
                close_time DATETIME,
                ai_confidence INTEGER,
                ai_reason TEXT
            )
        """)

        # learning_memory
        c.execute("""
            CREATE TABLE IF NOT EXISTS learning_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATETIME NOT NULL,
                market_context TEXT,
                result TEXT NOT NULL,
                lesson TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def save_trade(
        self,
        ticket: int,
        order_type: str,
        entry_price: float,
        close_price: float,
        profit: float,
        open_time: datetime,
        close_time: datetime,
        ai_confidence: int,
        ai_reason: str,
    ):
        """Simpan trade ke database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO trade_history
            (ticket, type, entry_price, close_price, profit, open_time, close_time, ai_confidence, ai_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket, order_type, entry_price, close_price, profit,
            open_time.isoformat(), close_time.isoformat(),
            ai_confidence, ai_reason
        ))
        conn.commit()
        conn.close()

    def save_lesson(
        self,
        market_context: Dict[str, Any],
        result: str,
        lesson: str,
    ):
        """Simpan lesson learned ke database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO learning_memory (date, market_context, result, lesson)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            str(market_context),
            result,
            lesson,
        ))
        conn.commit()
        conn.close()

    def get_recent_lessons(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Ambil N lesson terbaru"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM learning_memory
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_weighted_memory(
        self, limit_loss: int = 3, limit_win: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Ambil memory dengan weighted: lebih banyak loss daripada win.
        Ini membantu AI belajar dari kesalahan lebih banyak.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Ambil loss terbaru
        c.execute("""
            SELECT * FROM learning_memory
            WHERE result = 'LOSS'
            ORDER BY date DESC
            LIMIT ?
        """, (limit_loss,))
        loss_lessons = [dict(row) for row in c.fetchall()]

        # Ambil win terbaru
        c.execute("""
            SELECT * FROM learning_memory
            WHERE result = 'WIN'
            ORDER BY date DESC
            LIMIT ?
        """, (limit_win,))
        win_lessons = [dict(row) for row in c.fetchall()]

        conn.close()

        # Gabungkan: loss dulu, lalu win
        return loss_lessons + win_lessons

    def get_daily_stats(self) -> Dict[str, Any]:
        """Statistik trade hari ini"""
        today = date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losses,
                   SUM(profit) as total_profit
            FROM trade_history
            WHERE DATE(open_time) = ?
        """, (today,))

        row = c.fetchone()
        conn.close()

        return {
            "total_trades": row[0] or 0,
            "wins": row[1] or 0,
            "losses": row[2] or 0,
            "total_profit": row[3] or 0.0,
        }
