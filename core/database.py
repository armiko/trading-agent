"""
Database initialization dan setup.
Buat tabel jika belum ada, enable WAL mode.
"""
import sqlite3
import os


def init_database(db_path: str = "db/sqlite.db"):
    """Initialize database dengan semua tabel yang diperlukan"""
    # Pastikan direktori db ada
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Tabel trade_history
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

    # Tabel learning_memory
    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATETIME NOT NULL,
            market_context TEXT,
            result TEXT NOT NULL,
            lesson TEXT NOT NULL
        )
    """)

    # Index untuk performa query
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_trade_open_time 
        ON trade_history(open_time)
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_date 
        ON learning_memory(date)
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_result 
        ON learning_memory(result)
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {db_path}")


if __name__ == "__main__":
    init_database()
