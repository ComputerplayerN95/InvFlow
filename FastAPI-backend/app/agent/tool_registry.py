"""
工具注册表模式（Tool Registry Pattern）
---
核心思想：通过装饰器 @tool 将任意函数注册为 Agent 可调用的工具，
新增业务功能零侵入——只需写一个函数+加一行装饰器。
"""

import inspect
from typing import List, Dict, Any, Callable, Optional, get_type_hints
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

# 需要被框架注入、不在 Agent 参数列表中暴露的类型
_INJECTED_TYPES = ("Session", "AuditTrail")


class ToolRegistry:
    """全局工具注册表，管理所有可供 Agent 调用的业务工具"""

    _tools: Dict[str, Dict] = {}  # name -> {fn, description, args_schema, injected_params}

    @classmethod
    def register(cls, name: str = None, description: str = None, args_schema: type = None):
        """装饰器：将函数注册为 Agent 工具

        用法:
            @ToolRegistry.register()
            def query_stock(product_id: str, warehouse_id: str = "") -> str:
                \"\"\"查询库存\"\"\"
                ...

            @ToolRegistry.register(name="my_tool")
            def my_func(...):
                ...
        """
        def decorator(func: Callable):
            nonlocal name, description
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]
            sig = inspect.signature(func)
            hints = get_type_hints(func)

            # 识别哪些参数是框架注入的（不在 Agent 调用中暴露）
            injected_params = set()
            for pname, param in sig.parameters.items():
                ptype = hints.get(pname)
                if ptype and hasattr(ptype, "__name__") and ptype.__name__ in _INJECTED_TYPES:
                    injected_params.add(pname)

            # 如果没有提供 args_schema，自动生成（跳过注入参数）
            tool_args_schema = args_schema
            if tool_args_schema is None:
                fields = {}
                for pname, param in sig.parameters.items():
                    if pname in injected_params:
                        continue  # 跳过注入参数（由框架运行时提供）
                    ptype = hints.get(pname, str)
                    default = param.default
                    is_required = default is inspect.Parameter.empty
                    if not is_required:
                        fields[pname] = (Optional[ptype], Field(default=None, description=f"参数 {pname}"))
                    else:
                        fields[pname] = (ptype, Field(description=f"参数 {pname}"))
                if fields:
                    tool_args_schema = type(f"{tool_name}_args", (BaseModel,), {
                        "__annotations__": {k: v[0] for k, v in fields.items()},
                        **{k: v[1] for k, v in fields.items()}
                    })
                else:
                    tool_args_schema = type(f"{tool_name}_args", (BaseModel,), {})

            cls._tools[tool_name] = {
                "fn": func,
                "name": tool_name,
                "description": tool_desc,
                "args_schema": tool_args_schema,
                "injected_params": injected_params,
            }
            return func
        return decorator

    @classmethod
    def _inject_params(cls, info: dict, db=None, audit=None) -> dict:
        """为工具函数注入框架参数"""
        kwargs = {}
        if "db" in info["injected_params"] and db is not None:
            kwargs["db"] = db
        if "audit" in info["injected_params"] and audit is not None:
            kwargs["audit"] = audit
        return kwargs

    @classmethod
    def get_all_tools(cls, db=None) -> List[BaseTool]:
        """获取所有工具（转为 LangChain Tool 对象）"""
        tools = []
        # collect audit if any tool needs it
        audit = None
        for name, info in cls._tools.items():
            if "audit" in info["injected_params"]:
                from app.agent.audit import AuditTrail
                audit = AuditTrail(db)
                break

        for name, info in cls._tools.items():
            def make_tool(reg_name, reg_info):
                # 预计算注入参数（闭包绑定）
                injected = cls._inject_params(reg_info, db=db, audit=audit)

                def tool_func(*args, **kwargs):
                    # StructuredTool.invoke 把 dict 作为位置参数传入
                    # 需要合并 args[0] 和 kwargs
                    arg_dict = args[0] if args else {}
                    merged = {**injected, **arg_dict, **kwargs}
                    return reg_info["fn"](**merged)

                return StructuredTool(
                    name=reg_name,
                    description=reg_info["description"],
                    args_schema=reg_info["args_schema"],
                    func=tool_func,
                )

            tools.append(make_tool(name, info))
        return tools

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """列出所有已注册的工具"""
        return [
            {"name": name, "description": info["description"]}
            for name, info in cls._tools.items()
        ]
