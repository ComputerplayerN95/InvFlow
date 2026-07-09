"""Agent 配置"""
import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Agent 配置
AGENT_MAX_ITERATIONS = 10       # Agent 最大推理步数
AGENT_TIMEOUT = 60              # Agent 超时时间(秒)
AGENT_VERBOSE = True            # 是否输出详细日志

# RAG 配置
RAG_CHUNK_SIZE = 500
RAG_CHUNK_OVERLAP = 50
RAG_TOP_K = 3                   # 检索返回的最相关文档数
RAG_KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
RAG_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

# 运营审计身份
SYSTEM_AI_OPERATOR = "system_ai"
