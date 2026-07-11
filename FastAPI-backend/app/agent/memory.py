"""
持久化对话记忆（Persistent Chat Memory）
---
每次对话存入 ChatHistory 表，下次加载时回放上下文。
"""
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


DEFAULT_SESSION_ID = "default"
MAX_HISTORY = 20  # 最多保留 20 轮


def ensure_chat_table(db: Session):
    """确保 ChatHistory 表存在"""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ChatHistory (
                ChatID INT AUTO_INCREMENT PRIMARY KEY,
                SessionID VARCHAR(100) NOT NULL,
                Role VARCHAR(20) NOT NULL,
                Content TEXT NOT NULL,
                CreatedAt DATETIME DEFAULT NOW(),
                INDEX idx_session (SessionID, CreatedAt)
            )
        """))
        db.commit()
    except Exception:
        db.rollback()


class ChatMemory:
    """持久化对话记忆"""

    def __init__(self, db: Session, session_id: str = DEFAULT_SESSION_ID):
        self.db = db
        self.session_id = session_id

    def save(self, role: str, content: str):
        """保存一条对话记录"""
        try:
            self.db.execute(
                text("INSERT INTO ChatHistory (SessionID, Role, Content, CreatedAt) "
                     "VALUES (:sid, :role, :content, :ts)"),
                {"sid": self.session_id, "role": role,
                 "content": content, "ts": datetime.now()},
            )
            self.db.commit()
        except Exception as e:
            print(f"[ChatMemory] save error: {e}")
            self.db.rollback()

    def load(self, limit: int = MAX_HISTORY) -> List[Dict[str, str]]:
        """加载最近的对话记录"""
        try:
            rows = self.db.execute(
                text("SELECT Role, Content FROM ChatHistory "
                     "WHERE SessionID = :sid "
                     "ORDER BY CreatedAt ASC "
                     "LIMIT :lim"),
                {"sid": self.session_id, "lim": limit},
            ).mappings().all()
            return [{"role": r["Role"], "content": r["Content"]} for r in rows]
        except Exception as e:
            print(f"[ChatMemory] load error: {e}")
            return []

    def clear(self):
        """清空当前会话记录"""
        try:
            self.db.execute(
                text("DELETE FROM ChatHistory WHERE SessionID = :sid"),
                {"sid": self.session_id},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
