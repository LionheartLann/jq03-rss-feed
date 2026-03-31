import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "notices.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sent_notices (
    notice_id TEXT PRIMARY KEY,
    title     TEXT NOT NULL,
    sent_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class NoticeStore:
    def __init__(self, db_path: str | Path | None = None):
        self._db_path = str(db_path or DB_PATH)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def is_sent(self, notice_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sent_notices WHERE notice_id = ?", (notice_id,)
        ).fetchone()
        return row is not None

    def mark_sent(self, notice_id: str, title: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO sent_notices (notice_id, title) VALUES (?, ?)",
            (notice_id, title),
        )
        self._conn.commit()

    def filter_unsent(self, notices: list[dict]) -> list[dict]:
        """Return only notices that haven't been sent yet."""
        unsent = [n for n in notices if not self.is_sent(n.get("noticeId", ""))]
        logger.info("Dedup: %d new out of %d total", len(unsent), len(notices))
        return unsent

    def mark_all_sent(self, notices: list[dict]) -> None:
        for n in notices:
            self.mark_sent(n.get("noticeId", ""), n.get("title", ""))

    def close(self):
        self._conn.close()
