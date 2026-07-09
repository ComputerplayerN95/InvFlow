"""
Agent API 路由
---
提供聊天接口和工具管理接口。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.agent.agent import InvFlowAgent
from app.agent.audit import ensure_audit_table
from app.agent.tool_registry import ToolRegistry


router = APIRouter(prefix="/api/agent", tags=["AI智能助手"])


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    response: str
    audit_logs: Optional[list] = None


# 缓存 Agent 实例（按 db session 区分）
_agent_cache = {}


def get_agent(db: Session = Depends(get_db)) -> InvFlowAgent:
    """获取 Agent 实例"""
    # 确保审计表存在
    ensure_audit_table(db)
    return InvFlowAgent(db=db)


@router.post("/chat", response_model=ChatResponse)
def agent_chat(req: ChatRequest, agent: InvFlowAgent = Depends(get_agent)):
    """与 AI 智能助手对话"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    result = agent.chat(req.message, req.history or [])
    return ChatResponse(
        response=result["response"],
        audit_logs=result.get("audit_logs"),
    )


@router.get("/tools")
def list_tools(agent: InvFlowAgent = Depends(get_agent)):
    """列出所有可用的工具"""
    return {"tools": agent.list_tools()}


@router.post("/tools/{tool_name}/test")
def test_tool(tool_name: str, args: dict = {}, db: Session = Depends(get_db)):
    """手动测试某个工具（调试用）"""
    from app.agent.audit import AuditTrail
    audit = AuditTrail(db)
    tools = ToolRegistry.get_all_tools(db=db)
    for t in tools:
        if t.name == tool_name:
            try:
                result = t.invoke(input=args)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
    raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")
