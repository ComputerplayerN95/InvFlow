"""
审计留痕模块
---
所有 Agent 触发的数据库操作都以 system_ai 身份记录，
确保操作可追溯、可回滚。
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.agent.config import SYSTEM_AI_OPERATOR


class AuditTrail:
    """操作审计记录"""

    def __init__(self, db: Session):
        self.db = db
        self.logs = []

    def record(self, action: str, detail: dict, result: str = "success"):
        """记录一条审计日志"""
        entry = {
            "operator": SYSTEM_AI_OPERATOR,
            "action": action,
            "detail": json.dumps(detail, ensure_ascii=False),
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
        self.logs.append(entry)
        # 写入数据库 audit_log 表
        try:
            self.db.execute(
                text("INSERT INTO AuditLog (Operator, Action, Detail, Result, CreatedAt) "
                     "VALUES (:op, :action, :detail, :result, :ts)"),
                {"op": entry["operator"], "action": action,
                 "detail": entry["detail"], "result": result, "ts": datetime.now()}
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            # 如果 AuditLog 表不存在，静默失败（仅记录内存日志）

    def get_summary(self) -> list:
        return self.logs


def ensure_audit_table(db: Session):
    """确保审计表存在"""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                LogID INT AUTO_INCREMENT PRIMARY KEY,
                Operator VARCHAR(50) NOT NULL,
                Action VARCHAR(200) NOT NULL,
                Detail TEXT,
                Result VARCHAR(20) DEFAULT 'success',
                CreatedAt DATETIME DEFAULT NOW()
            )
        """))
        db.commit()
    except Exception:
        db.rollback()
