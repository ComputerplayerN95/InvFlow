"""
LangChain Agent 核心（LangGraph 版本）
---
使用 LangGraph 的 create_react_agent 创建 Agent，
通过 Tool Calling 方式自动编排业务操作。
"""
import os
import sys
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# Windows 编码修复：强制 Python 使用 UTF-8
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    AGENT_MAX_ITERATIONS,
)
from app.agent.tool_registry import ToolRegistry
from app.agent.audit import AuditTrail
from app.agent.memory import ChatMemory, ensure_chat_table


# System Prompt — Agent 的行为规范
AGENT_SYSTEM_PROMPT = """你是一个进销存管理系统（InvFlow）的智能业务助手，名叫"小库"。

## 严格规则 —— 必须遵守
你必须调用工具来获取任何数据，绝对不要凭你自己的知识回答数据类问题。

### 清单查询类问题
当用户问库存、采购、销售等数据：

第一步：调用对应的查询工具获取数据
第二步：看完工具返回的结果后，再用自然语言回答

### 业务流程操作类问题
当用户需要执行调拨、创建单据等操作：

第一步：先调用 check_shortage 或 query_stock 了解现状
第二步：根据数据生成方案，向用户展示并询问确认
第三步：用户确认后再执行操作

### 业务问答类问题
当用户问"FIFO是什么"、"怎么退货"等流程问题：

第一步：调用 business_qa 工具从知识库检索
第二步：结合工具返回的上下文和你的知识回答

## 可用工具
1. query_stock — 查库存（支持仓库名称如"北京总仓"或"北京仓"）
2. check_shortage — 检查缺货
3. generate_transfer_plan — 生成调拨方案
4. execute_transfer — 执行调拨
5. approve_ai_transfer — 审核调拨单
6. query_purchase_history — 查采购历史
7. query_sale_history — 查销售历史
8. business_qa — 回答流程问题（RAG知识库）

## 输出格式
使用自然语言回复，数据类问题用表格展示。
"""


class InvFlowAgent:
    """InvFlow 智能助手"""

    def __init__(self, db: Session, session_id: str = "default"):
        self.db = db
        ensure_chat_table(db)
        self.memory = ChatMemory(db, session_id)
        self.audit = AuditTrail(db)
        self.llm = self._init_llm()
        self.tools = ToolRegistry.get_all_tools(db=self.db)
        self.executor = self._init_executor()

    def _init_llm(self):
        """初始化大语言模型"""
        return ChatOpenAI(
            model=DEEPSEEK_MODEL,
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            temperature=0.1,
        )

    def _init_executor(self):
        """初始化 Agent 执行器（LangGraph ReAct Agent）"""
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=AGENT_SYSTEM_PROMPT,
        )

    def chat(self, user_input: str, history: List[Dict] = None) -> Dict[str, Any]:
        """处理用户消息，返回 Agent 回复"""
        # 持久化用户消息
        self.memory.save("user", user_input)

        messages = []

        # 从持久化存储加载历史 + 前端传入的历史（去重）
        db_history = self.memory.load(limit=10)
        # 如果前端传了 history 且比数据库更新，优先用前端的
        history_source = history if history else db_history

        # 加入历史消息
        if history_source:
            for msg in history_source[-10:]:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # 加入当前用户消息（如果不在历史中）
        has_current = any(
            isinstance(m, HumanMessage) and m.content == user_input
            for m in messages
        )
        if not has_current:
            messages.append(HumanMessage(content=user_input))

        try:
            result = self.executor.invoke({"messages": messages})
            output_messages = result.get("messages", [])
            # 取最后一条 AI 消息作为回复
            reply = ""
            for msg in reversed(output_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    reply = msg.content
                    break
            if not reply:
                reply = "处理完成，但没有生成文本回复。"

            self.audit.record("agent_chat", {
                "input": user_input[:200],
                "output": reply[:500],
            })

            # 持久化 AI 回复
            self.memory.save("assistant", reply)

            return {
                "response": reply,
                "audit_logs": self.audit.get_summary(),
            }
        except Exception as e:
            error_msg = f"处理出错: {str(e)}"
            self.audit.record("agent_error", {"input": user_input[:200], "error": str(e)}, result="failed")
            return {"response": error_msg, "audit_logs": self.audit.get_summary()}

    def list_tools(self) -> List[Dict]:
        """列出可用工具"""
        return ToolRegistry.list_tools()
