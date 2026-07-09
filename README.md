# InvFlow 进销存管理系统

> 基于 FastAPI + Vue 3 的中小企业进销存管理系统，支持 FIFO 先进先出成本核算与 AI 智能助手。

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen)](https://vuejs.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 项目简介

InvFlow 是一个面向中小企业的进销存（库存/采购/销售/调拨）管理系统，提供完整的业务流转和库存管理功能。系统采用 **FIFO 先进先出法** 和 **移动加权平均法** 两种成本核算方式，并集成 **AI 智能助手**，支持自然语言指令驱动的业务操作。
<img width="1920" height="952" alt="image" src="https://github.com/user-attachments/assets/f251b550-166e-44f7-b95a-2e9176ab3c77" />


### 核心功能一览

| 模块 | 功能 |
|------|------|
| 📦 基础数据管理 | 商品、仓库、供应商、客户 CRUD |
| 🛒 采购管理 | 采购单创建/入库/回退，自动创建批次库存 |
| 💰 销售管理 | 销售单创建/出库/回退，FIFO 成本扣减 |
| 🔄 调拨管理 | 跨仓库调拨，审核自动同步出入库 |
| 📊 库存查询 | 库存总表、仓库库存、月度结存 |
| 🔙 采购退货 | 精确按采购批次退货扣减 |
| 🔙 销售退货 | 按出库批次原路恢复库存 |
| ✅ 盘点管理 | 盘点单审核自动生成损益单 |
| 📈 FIFO 报表 | 先进先出 vs 均价法成本/毛利对比 |
| 🤖 AI 智能助手 | 自然语言驱动，自动查库存/调拨/问答 |

---

## 🏗 技术栈

```
┌────────────────────────────────────────────┐
│   前端: Vue 3 + Element Plus + Vite 6      │
│   SPA + Axios → Vite Proxy → FastAPI       │
├────────────────────────────────────────────┤
│   后端: FastAPI + SQLAlchemy + PyMySQL      │
│   LangChain Agent + DeepSeek LLM           │
├────────────────────────────────────────────┤
│   数据库: MySQL 8.0 + InnoDB               │
│   20+ 表 / 6 个触发器 / 6 个存储过程        │
└────────────────────────────────────────────┘
```

- **前端**: Vue 3 (Composition API) + Element Plus + Vite 6
- **后端**: FastAPI + SQLAlchemy 2.0 + PyMySQL
- **数据库**: MySQL 8.0（utf8mb4 编码）
- **AI**: LangChain + LangGraph + DeepSeek API + ChromaDB（RAG）
- **测试**: pytest + unittest.mock（42 个单元测试）

---

## 🚀 快速开始

### 前置条件

- Python 3.13+
- Node.js 22+
- MySQL 8.0

### 1. 克隆项目

```bash
git clone https://github.com/ComputerplayerN95/InvFlow.git
cd InvFlow
```

### 2. 数据库初始化

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS `invflow-db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 执行升级脚本
source FastAPI-backend/sql/upgrade_v2.sql;
source FastAPI-backend/sql/fix_triggers_charset.sql;
```

### 3. 启动后端

```bash
cd FastAPI-backend

# 创建虚拟环境（如尚未创建）
python -m venv venv

# 安装依赖
pip install -r requirements.txt

# 配置数据库（编辑 app/config.py）
# DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# 启动（Windows 需要 PYTHONUTF8=1）
PYTHONUTF8=1 ./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档：`http://localhost:8000/docs`

### 4. 启动前端

```bash
cd vue-frontend
npm install
npm run dev
```

前端地址：`http://localhost:5173`

### 5. 配置 AI 助手（可选）

编辑 `FastAPI-backend/.env`：

```env
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

---

## 🤖 AI 智能助手

系统集成基于 **LangChain + LangGraph** 的 AI 智能助手"小库"，支持自然语言驱动的业务操作。

### 功能

| 操作 | 自然语言指令示例 |
|------|----------------|
| 查库存 | "帮我查一下北京仓的库存" |
| 查缺货 | "P001 够不够 50 件" |
| 自动调拨 | "P001 不够的话从上海调 5 件到北京" |
| 查采购 | "这个月有采购记录吗" |
| 查销售 | "查一下 P001 的销售记录" |
| 流程问答 | "FIFO 先进先出法是什么"、"怎么做采购退货" |

### 技术实现

- **工具注册表模式**：`@ToolRegistry.register()` 装饰器零侵入注册
- **LangGraph ReAct Agent**：DeepSeek 驱动，多步推理自动编排
- **RAG 引擎**：ChromaDB 向量库，基于业务文档回答流程问题
- **审计留痕**：所有 AI 操作以 `system_ai` 身份记录到 `AuditLog` 表

```
用户输入"P001不够就从上海调到北京"
  ↓
Agent: query_stock('P001') → 北京仓仅 1 件
  ↓
Agent: check_shortage('P001', 5) → 缺货
  ↓
Agent: generate_transfer_plan('P001', '北京', 5) → 从上海调 5 件
  ↓
Agent: 展示方案 → 询问用户确认
  ↓
用户确认 → Agent: execute_transfer(...) → 调拨单创建成功
```

---

## 📁 项目结构

```
InvFlow/
├── FastAPI-backend/
│   ├── app/
│   │   ├── main.py                # FastAPI 应用入口
│   │   ├── config.py              # 数据库/应用配置
│   │   ├── database.py            # SQLAlchemy 引擎
│   │   ├── models.py              # ORM 模型（20+ 表）
│   │   ├── schemas.py             # Pydantic 请求/响应模型
│   │   ├── routers/               # API 路由
│   │   │   ├── purchase.py        # 采购管理
│   │   │   ├── sale.py            # 销售管理
│   │   │   ├── transfer.py        # 调拨管理
│   │   │   ├── returns.py         # 采购/销售退货
│   │   │   ├── stock_check.py     # 盘点/损益
│   │   │   └── reports.py         # 报表 + FIFO 报表
│   │   ├── utils/
│   │   │   └── stock_utils.py     # FIFO 核心逻辑
│   │   └── agent/                 # AI 智能助手
│   │       ├── tool_registry.py   # 工具注册表
│   │       ├── tools.py           # 8 个业务工具
│   │       ├── agent.py           # LangGraph Agent
│   │       ├── rag.py             # RAG 引擎
│   │       ├── audit.py           # 审计留痕
│   │       └── router.py          # Chat API
│   ├── sql/
│   │   ├── upgrade_v2.sql         # v2 升级 DDL
│   │   └── fix_triggers_charset.sql # 触发器编码修复
│   └── tests/
│       └── test_invflow_upgrade_v2.py  # 42 个单元测试
├── vue-frontend/
│   ├── src/
│   │   ├── api/index.js           # Axios API 层
│   │   ├── router/index.js        # 前端路由
│   │   ├── components/            # 公共组件
│   │   │   ├── CrudTable.vue      # 通用 CRUD 表格
│   │   │   ├── StatusTag.vue      # 状态标签
│   │   │   └── ChatAssistant.vue  # AI 聊天助手
│   │   └── views/                 # 14 个页面视图
│   └── vite.config.js             # Vite 配置 + 代理
└── README.md
```

---

## 🔑 核心设计：FIFO 先进先出法

### 实现原理

每次采购入库时，系统在 `BatchStock` 表中记录入库批次（含单价）。销售出库时，按入库时间从最早的批次开始扣减。

```
批次1: 进货 10 件 @ 10 元 (1 月)
批次2: 进货 10 件 @ 12 元 (2 月)

销售 8 件 → 从批次 1 扣: 成本 = 8 × 10 = 80 元
销售 5 件 → 批次 1 剩 2 + 批次 2 扣 3: 2×10 + 3×12 = 56 元

FIFO 总成本 = 136 元  |  均价法总成本 = 143 元
```

### 相关表

- `BatchStock` — 批次库存（含单价、剩余量）
- `SaleOutBatch` — 销售出库批次记录（支持退货恢复）

### 核心代码（简化）

```python
def fifo_deduct_with_detail(db, product_id, warehouse_id, quantity):
    batches = db.query(BatchStock).filter(
        BatchStock.RemainingQty > 0
    ).order_by(BatchStock.InDate.asc()).all()

    result = []
    remaining = quantity
    for batch in batches:
        if remaining <= 0:
            break
        deduct = min(batch.RemainingQty, remaining)
        result.append({"BatchID": batch.BatchID,
                       "Quantity": deduct,
                       "UnitPrice": float(batch.UnitPrice)})
        batch.RemainingQty -= deduct
        remaining -= deduct
    return result
```

---

## 📸 API 文档

启动后端后访问 `http://localhost:8000/docs` 查看完整的 Swagger API 文档。

主要 API 端点：

| 分类 | 端点前缀 | 说明 |
|------|---------|------|
| 基础数据 | `/api/categories/`, `/api/warehouses/`, `/api/suppliers/`, `/api/customers/`, `/api/products/` | CRUD |
| 采购 | `/api/purchases/` | 采购单 + 入库/回退 |
| 销售 | `/api/sales/` | 销售单 + 出库/回退 |
| 调拨 | `/api/transfers/` | 调拨单 + 审核/回退 |
| 库存 | `/api/stock/` | 总表/仓库/月度 |
| 退货 | `/api/purchase-returns/`, `/api/sale-returns/` | 退货单 + 执行/回退 |
| 盘点 | `/api/stock-checks/` | 盘点单 + 审核/回退 |
| 损益 | `/api/profit-loss/` | 损益单 + 审核/回退 |
| 报表 | `/api/reports/` | 月度明细/FIFO 毛利/成本对比 |
| AI 助手 | `/api/agent/chat` | 自然语言对话 |

---

## 🧪 测试

```bash
cd FastAPI-backend
./venv/Scripts/python -m pytest tests/ -v
```

测试覆盖：FIFO 扣减、采购退货、销售退货、盘点损益、Schema 验证、API 路由（共 42 个测试用例）。

---

## 🐛 常见问题

### 后端启动报端口占用
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Windows 中文编码错误
```bash
# 启动时加 PYTHONUTF8=1 环境变量
PYTHONUTF8=1 python -m uvicorn app.main:app --reload
```

### MySQL 1267 collation 错误
确保 `database.py` 中 DATABASE_URL 包含 `?charset=utf8mb4`。如果已加仍报错，执行 `sql/fix_triggers_charset.sql` 修复触发器编码。

---

## 📄 License

MIT License

## 👤 作者

N95-LLLJD
