"""
Learning Memory: Mengelola SQLite database untuk trade history dan self-reflection.
- trade_history: catat semua trade
- learning_memory: catat lesson learned dari AI
- FIX #15: Database timeout + retry untuk concurrent access
- FIX #18: Configurable weighted memory
"""
import sqlite3
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import requests
import threading

def _push_telemetry(url: str, api_key: str, endpoint: str, payload: dict):
    if not url or not api_key:
        return
    try:
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        requests.post(f"{url.rstrip('/')}/{endpoint}", json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"[Telemetry Sync Failed] {e}")

class LearningMemory:
    def __init__(self, db_path: str = "db/sqlite.db", loss_count: int = 3, win_count: int = 2, saas_backend_url: str = "", saas_api_key: str = ""):
        self.db_path = db_path
        self.loss_count = loss_count
        self.win_count = win_count
        self.db_timeout = 30
        self.saas_backend_url = saas_backend_url
        self.saas_api_key = saas_api_key
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """FIX #15: Get connection dengan timeout"""
        conn = sqlite3.connect(self.db_path, timeout=self.db_timeout)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")  # 5 detik retry
        return conn

    def _init_db(self):
        """Buat tabel jika belum ada (WAL mode enabled)"""
        conn = self._get_conn()
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
        conn = self._get_conn()
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
        
        # Async push to SaaS
        symbol = ai_reason.split()[0] if " " in ai_reason else "UNKNOWN"  # simplified extraction
        payload = {
            "symbol": symbol,
            "action": order_type,
            "profit": profit,
            "ai_reason": ai_reason,
            "close_time": close_time.isoformat()
        }
        threading.Thread(target=_push_telemetry, args=(self.saas_backend_url, self.saas_api_key, "telemetry/trade", payload)).start()

    def save_lesson(
        self,
        market_context: Dict[str, Any],
        result: str,
        lesson: str,
    ):
        """Simpan lesson learned ke database"""
        conn = self._get_conn()
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
        
        # Async push to SaaS
        symbol = market_context.get("symbol", "UNKNOWN")
        payload = {
            "symbol": symbol,
            "context_summary": str(market_context),
            "lesson": lesson,
            "result": result
        }
        threading.Thread(target=_push_telemetry, args=(self.saas_backend_url, self.saas_api_key, "telemetry/lesson", payload)).start()

    def get_recent_lessons(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Ambil N lesson terbaru"""
        conn = self._get_conn()
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
        self, limit_loss: int = None, limit_win: int = None
    ) -> List[Dict[str, Any]]:
        """
        FIX #18: Ambil memory dengan weighted (configurable via constructor).
        Default: 3 loss + 2 win. Bisa diubah di config.yaml.
        """
        limit_loss = limit_loss or self.loss_count
        limit_win = limit_win or self.win_count
        
        conn = self._get_conn()
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

    def get_contextual_memory(self, current_context: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Ambil memory yang konteksnya mirip dengan kondisi saat ini.
        """
        import ast
        
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Ambil history terbaru untuk difilter
        c.execute("""
            SELECT * FROM learning_memory
            ORDER BY date DESC
            LIMIT 50
        """)
        rows = c.fetchall()
        conn.close()
        
        current_session = current_context.get("session", "UNKNOWN")
        current_regime = current_context.get("regime", "UNKNOWN")
        current_rsi = current_context.get("rsi", 50)
        
        scored_lessons = []
        for row in rows:
            lesson_dict = dict(row)
            try:
                mc_str = lesson_dict.get("market_context", "{}")
                mc = ast.literal_eval(mc_str)
            except:
                mc = {}
                
            score = 0
            if mc.get("session") == current_session:
                score += 2
            if mc.get("regime") == current_regime:
                score += 2
                
            mem_rsi = mc.get("rsi", 50)
            if abs(mem_rsi - current_rsi) <= 15:
                score += 1
                
            # Hanya ambil yang cukup mirip
            if score >= 3:
                scored_lessons.append((score, lesson_dict))
                
        scored_lessons.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_lessons[:limit]]

    def get_daily_stats(self) -> Dict[str, Any]:
        """Statistik trade hari ini"""
        today = date.today().isoformat()
        conn = self._get_conn()
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
