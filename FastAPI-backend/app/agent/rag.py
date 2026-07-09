"""
RAG 引擎
---
基于业务文档（INVFLOW_KNOWLEDGE_BASE.md）构建向量知识库，
Agent 可通过 query_document 工具检索业务流程相关信息。
"""
import os
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader

from app.agent.config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_TOP_K,
    RAG_KNOWLEDGE_DIR, RAG_PERSIST_DIR,
)


_rag_engine = None  # 单例


def get_rag_engine():
    """获取 RAG 引擎（单例，懒加载）"""
    global _rag_engine
    if _rag_engine is not None:
        return _rag_engine
    _rag_engine = RAGEngine()
    return _rag_engine


class RAGEngine:
    """基于 ChromaDB 的 RAG 检索引擎"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
        )
        self.vector_store = None
        self._init_or_load()

    def _init_or_load(self):
        """初始化或加载已有向量库"""
        if os.path.exists(RAG_PERSIST_DIR) and os.listdir(RAG_PERSIST_DIR):
            # 已有持久化向量库，直接加载
            self.vector_store = Chroma(
                persist_directory=RAG_PERSIST_DIR,
                embedding_function=self.embeddings,
            )
        else:
            # 从知识文档构建
            self._build_from_docs()

    def _build_from_docs(self):
        """从 knowledge/ 目录加载文档构建向量库"""
        docs = []
        if os.path.exists(RAG_KNOWLEDGE_DIR):
            for fname in os.listdir(RAG_KNOWLEDGE_DIR):
                fpath = os.path.join(RAG_KNOWLEDGE_DIR, fname)
                if fname.endswith(".md") or fname.endswith(".txt"):
                    try:
                        loader = TextLoader(fpath, encoding="utf-8")
                        docs.extend(loader.load())
                    except Exception as e:
                        print(f"[RAG] 加载文档失败 {fname}: {e}")

        if not docs:
            print("[RAG] 无知识文档，使用占位文档")
            docs = [Document(
                page_content="InvFlow 进销存管理系统支持采购、销售、调拨、退货、盘点等完整业务流程。"
                             "FIFO 先进先出法按入库时间逐批扣减库存。",
                metadata={"source": "builtin"},
            )]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(docs)

        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=RAG_PERSIST_DIR,
        )
        self.vector_store.persist()

    def search(self, query: str, k: int = None) -> List[str]:
        """检索与 query 最相关的 k 段文档"""
        if self.vector_store is None:
            return []
        k = k or RAG_TOP_K
        results = self.vector_store.similarity_search(query, k=k)
        return [doc.page_content for doc in results]

    def get_context(self, query: str) -> str:
        """获取检索结果拼接为上下文文本"""
        results = self.search(query)
        if not results:
            return ""
        sections = [f"[参考文档 {i+1}]\n{text}" for i, text in enumerate(results)]
        return "\n\n".join(sections)
