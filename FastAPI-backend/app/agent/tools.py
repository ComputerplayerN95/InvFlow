"""
Agent 业务工具集
---
所有工具通过 @ToolRegistry.register() 注册，
自动生成参数 Schema，零侵入新增业务功能。
"""
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.agent.tool_registry import ToolRegistry
from app.agent.audit import AuditTrail


# ==================== 辅助函数 ====================

def _resolve_warehouse(db: Session, warehouse_input: str) -> tuple:
    """将仓库名称解析为 ID，返回 (warehouse_id, warehouse_name, error_msg)"""
    if not warehouse_input:
        return "", "", ""
    # 已经是标准 ID 格式
    if warehouse_input.startswith(("WH", "wh")):
        row = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
                         {"wid": warehouse_input}).mappings().first()
        if row:
            return row["WarehouseID"], row["WarehouseName"], ""
        return "", "", f"仓库编号 {warehouse_input} 不存在"
    # 按名称精确匹配
    row = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseName = :wname"),
                     {"wname": warehouse_input}).mappings().first()
    if row:
        return row["WarehouseID"], row["WarehouseName"], ""
    # 按名称模糊匹配
    rows = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseName LIKE :wname"),
                      {"wname": f"%{warehouse_input}%"}).mappings().all()
    if len(rows) == 1:
        return rows[0]["WarehouseID"], rows[0]["WarehouseName"], ""
    if len(rows) > 1:
        names = "、".join([f"{r['WarehouseName']}({r['WarehouseID']})" for r in rows])
        return "", "", f"'{warehouse_input}' 匹配到多个仓库：{names}，请使用仓库编号"
    # 如果模糊匹配不到，尝试用城市名匹配（去掉"仓""库""仓库"等后缀）
    # 如 "北京仓" → 提取 "北京" 再匹配
    for suffix in ["仓库", "分仓", "总仓", "仓", "库"]:
        if warehouse_input.endswith(suffix):
            core = warehouse_input[:-len(suffix)]
            if core:
                rows2 = db.execute(
                    text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseName LIKE :cname"),
                    {"cname": f"%{core}%"}
                ).mappings().all()
                if rows2:
                    names = "、".join([f"{r['WarehouseName']}({r['WarehouseID']})" for r in rows2])
                    if len(rows2) == 1:
                        return rows2[0]["WarehouseID"], rows2[0]["WarehouseName"], ""
                    return "", "", f"'{warehouse_input}' 匹配到多个：{names}"
    # 查不到时列出所有仓库
    all_wh = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse")).mappings().all()
    wh_list = "、".join([f"{r['WarehouseName']}({r['WarehouseID']})" for r in all_wh])
    return "", "", f"未找到仓库 '{warehouse_input}'，系统中有：{wh_list}"


# ==================== 库存查询工具 ====================

@ToolRegistry.register()
def query_stock(db: Session, product_id: str = "", warehouse_id: str = "") -> str:
    """查询商品库存。product_id: 商品编号(可选,不传查全部), warehouse_id: 仓库编号或名称(可选)"""
    # None → '' 统一处理，避免 SQL 比较失效
    pid = product_id or ""
    wid, wname, err = _resolve_warehouse(db, warehouse_id) if warehouse_id else ("", "", "")
    if err:
        return json.dumps({"found": False, "message": err}, ensure_ascii=False)

    sql = """
        SELECT ws.ProductID, p.ProductName, ws.WarehouseID, w.WarehouseName, ws.Quantity
        FROM WarehouseStock ws
        JOIN Product p ON ws.ProductID = p.ProductID
        JOIN Warehouse w ON ws.WarehouseID = w.WarehouseID
        WHERE (ws.ProductID = :pid OR :pid = '')
          AND (ws.WarehouseID = :wid OR :wid = '')
        ORDER BY ws.ProductID, ws.WarehouseID
    """
    rows = db.execute(text(sql), {"pid": pid, "wid": wid}).mappings().all()
    if not rows:
        return json.dumps({"found": False, "message": "未找到匹配的库存记录"}, ensure_ascii=False)
    result = []
    for r in rows:
        result.append({
            "product_id": r["ProductID"],
            "product_name": r["ProductName"],
            "warehouse_id": r["WarehouseID"],
            "warehouse_name": r["WarehouseName"],
            "quantity": float(r["Quantity"]),
        })
    return json.dumps({"found": True, "items": result}, ensure_ascii=False)


@ToolRegistry.register()
def check_shortage(db: Session, product_id: str, required_qty: float) -> str:
    """检查某个商品是否存在缺货。product_id: 商品编号, required_qty: 需求量"""
    sql = """
        SELECT ws.WarehouseID, w.WarehouseName, ws.Quantity
        FROM WarehouseStock ws
        JOIN Warehouse w ON ws.WarehouseID = w.WarehouseID
        WHERE ws.ProductID = :pid AND ws.Quantity > 0
        ORDER BY ws.Quantity DESC
    """
    rows = db.execute(text(sql), {"pid": product_id}).mappings().all()

    total = sum(float(r["Quantity"]) for r in rows)
    shortage = max(0, required_qty - total)

    result = {
        "product_id": product_id,
        "required_qty": required_qty,
        "total_stock": total,
        "shortage": shortage,
        "sufficient": shortage <= 0,
        "warehouses": [
            {"warehouse_id": r["WarehouseID"], "warehouse_name": r["WarehouseName"],
             "quantity": float(r["Quantity"])}
            for r in rows
        ]
    }
    if shortage > 0:
        result["message"] = f"库存不足，缺货 {shortage} 件，当前总量 {total} 件"
    else:
        result["message"] = f"库存充足，当前总量 {total} 件，满足需求"
    return json.dumps(result, ensure_ascii=False)


# ==================== 调拨方案工具 ====================

@ToolRegistry.register()
def generate_transfer_plan(db: Session, product_id: str, target_warehouse_id: str, quantity: float) -> str:
    """生成调拨方案。product_id: 商品, target_warehouse_id: 目标仓库编号或名称, quantity: 调拨数量"""
    twid, twname, err = _resolve_warehouse(db, target_warehouse_id)
    if err:
        return json.dumps({"feasible": False, "message": err}, ensure_ascii=False)
    # 排除目标仓库，找有库存的仓库
    sql = """
        SELECT ws.WarehouseID, w.WarehouseName, ws.Quantity
        FROM WarehouseStock ws
        JOIN Warehouse w ON ws.WarehouseID = w.WarehouseID
        WHERE ws.ProductID = :pid AND ws.WarehouseID != :twid AND ws.Quantity > 0
        ORDER BY ws.Quantity DESC
    """
    rows = db.execute(text(sql), {"pid": product_id, "twid": twid}).mappings().all()

    if not rows:
        return json.dumps({"feasible": False, "message": "无可用的调出仓库"}, ensure_ascii=False)

    # 找可用库存最大的仓库
    source = rows[0]
    available = float(source["Quantity"])
    can_transfer = min(available, quantity)

    plan = {
        "feasible": True,
        "product_id": product_id,
        "source_warehouse_id": source["WarehouseID"],
        "source_warehouse_name": source["WarehouseName"],
        "target_warehouse_id": twid,
        "target_warehouse_name": twname or target_warehouse_id,
        "requested_qty": quantity,
        "available_in_source": available,
        "transfer_qty": can_transfer,
        "sufficient": available >= quantity,
        "message": f"可从 {source['WarehouseName']} 调拨 {can_transfer} 件"
                    + ("" if available >= quantity else f"（该仓仅剩 {available} 件）"),
    }
    return json.dumps(plan, ensure_ascii=False)


@ToolRegistry.register()
def execute_transfer(db: Session, audit: AuditTrail,
                     product_id: str, source_warehouse_id: str, target_warehouse_id: str,
                     quantity: float, operator: str = "system_ai") -> str:
    """执行调拨。product_id: 商品, source_warehouse_id: 调出仓(编号或名称), target_warehouse_id: 调入仓(编号或名称), quantity: 数量"""
    # 解析仓库名称 → ID
    swid, _, serr = _resolve_warehouse(db, source_warehouse_id)
    if serr:
        return json.dumps({"success": False, "error": serr}, ensure_ascii=False)
    twid, _, terr = _resolve_warehouse(db, target_warehouse_id)
    if terr:
        return json.dumps({"success": False, "error": terr}, ensure_ascii=False)
    from app.models import TransferOrder, TransferDetail

    now = datetime.now()
    transfer_id = f"AI{now.strftime('%Y%m%d%H%M%S')}"
    detail_id = f"AID{now.strftime('%Y%m%d%H%M%S')}01"

    try:
        order = TransferOrder(
            TransferID=transfer_id,
            FromWarehouseID=swid,
            ToWarehouseID=twid,
            OrderDate=now,
            Status="草稿",
            Operator=operator,
        )
        db.add(order)
        db.flush()
        db.add(TransferDetail(
            TransferDetailID=detail_id,
            TransferID=transfer_id,
            ProductID=product_id,
            Quantity=quantity,
        ))
        db.commit()

        audit.record("execute_transfer", {
            "transfer_id": transfer_id, "product_id": product_id,
            "from": swid, "to": twid, "qty": quantity,
        })

        return json.dumps({
            "success": True,
            "transfer_id": transfer_id,
            "message": f"调拨单 {transfer_id} 已创建（草稿状态），如需审核请调用审核接口",
        }, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        audit.record("execute_transfer", {
            "product_id": product_id, "qty": quantity,
        }, result=f"failed: {str(e)}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@ToolRegistry.register()
def approve_ai_transfer(db: Session, audit: AuditTrail, transfer_id: str) -> str:
    """审核 AI 创建的调拨单。transfer_id: 调拨单编号"""
    from app.routers.transfer import approve_transfer as real_approve
    from fastapi import HTTPException
    try:
        result = real_approve(transfer_id, db)
        audit.record("approve_transfer", {"transfer_id": transfer_id, "result": str(result)})
        return json.dumps({"success": True, "message": f"调拨单 {transfer_id} 审核通过"}, ensure_ascii=False)
    except HTTPException as e:
        return json.dumps({"success": False, "error": e.detail}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ==================== 采购/销售查询工具 ====================

@ToolRegistry.register()
def query_purchase_history(db: Session, product_id: str = "", limit: int = 5) -> str:
    """查询采购历史。product_id: 商品编号(可选), limit: 返回条数"""
    pid = product_id or ""
    sql = """
        SELECT po.PurchaseID, po.SupplierID, s.SupplierName,
               pd.ProductID, p.ProductName, pd.Quantity, pd.UnitPrice, pd.Amount,
               po.Status, po.OrderDate
        FROM PurchaseOrder po
        JOIN PurchaseDetail pd ON po.PurchaseID = pd.PurchaseID
        JOIN Supplier s ON po.SupplierID = s.SupplierID
        JOIN Product p ON pd.ProductID = p.ProductID
        WHERE (pd.ProductID = :pid OR :pid = '')
        ORDER BY po.OrderDate DESC
        LIMIT :lim
    """
    rows = db.execute(text(sql), {"pid": pid, "lim": limit}).mappings().all()
    items = [dict(r) for r in rows]
    return json.dumps({"found": len(items) > 0, "items": items}, ensure_ascii=False, default=str)


@ToolRegistry.register()
def query_sale_history(db: Session, product_id: str = "", limit: int = 5) -> str:
    """查询销售历史。product_id: 商品编号(可选), limit: 返回条数"""
    pid = product_id or ""
    sql = """
        SELECT so.SaleID, so.CustomerID, c.CustomerName,
               sd.ProductID, p.ProductName, sd.Quantity, sd.UnitPrice, sd.Amount,
               so.Status, so.OrderDate
        FROM SaleOrder so
        JOIN SaleDetail sd ON so.SaleID = sd.SaleID
        JOIN Customer c ON so.CustomerID = c.CustomerID
        JOIN Product p ON sd.ProductID = p.ProductID
        WHERE (sd.ProductID = :pid OR :pid = '')
        ORDER BY so.OrderDate DESC
        LIMIT :lim
    """
    rows = db.execute(text(sql), {"pid": pid, "lim": limit}).mappings().all()
    items = [dict(r) for r in rows]
    return json.dumps({"found": len(items) > 0, "items": items}, ensure_ascii=False, default=str)


# ==================== 业务问答工具（RAG）====================

@ToolRegistry.register()
def business_qa(query: str) -> str:
    """回答关于进销存业务流程的问题（如：如何创建采购单？FIFO是什么？怎么退货？）。
       基于知识库检索。query: 用户问题"""
    try:
        from app.agent.rag import get_rag_engine
        engine = get_rag_engine()
        context = engine.get_context(query)
        if context:
            return json.dumps({
                "found": True,
                "context": context,
                "instruction": "请基于以上参考文档回答用户的问题，如果文档信息不足，请结合你的知识补充。"
            }, ensure_ascii=False)
        else:
            return json.dumps({"found": False, "message": "知识库中未找到相关信息"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"found": False, "error": str(e)}, ensure_ascii=False)


# ==================== 创建工具（ID自动递增）====================

def _next_id(db: Session, table: str, prefix: str, pad: int = 3) -> str:
    """生成下一个递增编号，如 WH001 → WH004"""
    try:
        rows = db.execute(text(f"SELECT {table}ID FROM `{table}` ORDER BY LENGTH({table}ID) DESC, {table}ID DESC LIMIT 1")).mappings().all()
        if rows:
            last = rows[0][f"{table}ID"]
            num = int(last[len(prefix):]) + 1
        else:
            num = 1
        return f"{prefix}{str(num).zfill(pad)}"
    except Exception:
        return f"{prefix}{'001'}"


@ToolRegistry.register()
def create_warehouse(db: Session,
                     name: str = "", location: str = "", phone: str = "",
                     warehouse_id: str = "") -> str:
    """创建仓库。name:仓库名称, location:地址(可选), phone:电话(可选), warehouse_id:编号(不传自动生成)"""
    missing = []
    if not name:
        missing.append("仓库名称(name)")
    if missing:
        return json.dumps({"complete": False, "missing": missing,
                           "hint": "请提供仓库名称"}, ensure_ascii=False)
    wid = warehouse_id or _next_id(db, "Warehouse", "WH")
    # 检查是否已存在
    exists = db.execute(text("SELECT COUNT(*) FROM Warehouse WHERE WarehouseID = :id"), {"id": wid}).scalar()
    if exists:
        wid = _next_id(db, "Warehouse", "WH")
    try:
        db.execute(text("INSERT INTO Warehouse (WarehouseID, WarehouseName, Location, Phone) VALUES (:id, :n, :l, :p)"),
                   {"id": wid, "n": name, "l": location or None, "p": phone or None})
        db.commit()
        return json.dumps({"complete": True, "success": True, "id": wid,
                           "message": f"仓库 {wid}({name}) 创建成功"}, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        return json.dumps({"complete": False, "success": False, "error": str(e)}, ensure_ascii=False)


@ToolRegistry.register()
def create_supplier(db: Session,
                    name: str = "", contact: str = "", phone: str = "",
                    address: str = "", remark: str = "",
                    supplier_id: str = "") -> str:
    """创建供应商。name:供应商名称(必填), contact:联系人(可选), phone:电话(可选), address:地址(可选), remark:备注(可选), supplier_id:编号(不传自动生成)"""
    missing = []
    if not name:
        missing.append("供应商名称(name)")
    if missing:
        return json.dumps({"complete": False, "missing": missing,
                           "hint": "请提供供应商名称"}, ensure_ascii=False)
    sid = supplier_id or _next_id(db, "Supplier", "SUP")
    exists = db.execute(text("SELECT COUNT(*) FROM Supplier WHERE SupplierID = :id"), {"id": sid}).scalar()
    if exists:
        sid = _next_id(db, "Supplier", "SUP")
    try:
        db.execute(text("INSERT INTO Supplier (SupplierID, SupplierName, ContactPerson, Phone, Address, Remark) VALUES (:id, :n, :c, :p, :a, :r)"),
                   {"id": sid, "n": name, "c": contact or None, "p": phone or None,
                    "a": address or None, "r": remark or None})
        db.commit()
        return json.dumps({"complete": True, "success": True, "id": sid,
                           "message": f"供应商 {sid}({name}) 创建成功"}, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        return json.dumps({"complete": False, "success": False, "error": str(e)}, ensure_ascii=False)


@ToolRegistry.register()
def create_customer(db: Session,
                    name: str = "", contact: str = "", phone: str = "",
                    address: str = "", remark: str = "",
                    customer_id: str = "") -> str:
    """创建客户。name:客户名称(必填), contact:联系人(可选), phone:电话(可选), address:地址(可选), remark:备注(可选), customer_id:编号(不传自动生成)"""
    missing = []
    if not name:
        missing.append("客户名称(name)")
    if missing:
        return json.dumps({"complete": False, "missing": missing,
                           "hint": "请提供客户名称"}, ensure_ascii=False)
    cid = customer_id or _next_id(db, "Customer", "CUS")
    exists = db.execute(text("SELECT COUNT(*) FROM Customer WHERE CustomerID = :id"), {"id": cid}).scalar()
    if exists:
        cid = _next_id(db, "Customer", "CUS")
    try:
        db.execute(text("INSERT INTO Customer (CustomerID, CustomerName, ContactPerson, Phone, Address, Remark) VALUES (:id, :n, :c, :p, :a, :r)"),
                   {"id": cid, "n": name, "c": contact or None, "p": phone or None,
                    "a": address or None, "r": remark or None})
        db.commit()
        return json.dumps({"complete": True, "success": True, "id": cid,
                           "message": f"客户 {cid}({name}) 创建成功"}, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        return json.dumps({"complete": False, "success": False, "error": str(e)}, ensure_ascii=False)


@ToolRegistry.register()
def create_product(db: Session,
                   name: str = "", category_id: str = "", spec: str = "",
                   unit: str = "", remark: str = "",
                   product_id: str = "") -> str:
    """创建商品。name:商品名称(必填), category_id:类别编号(必填,如C001), spec:规格(可选), unit:单位(可选), remark:备注(可选), product_id:编号(不传自动生成)"""
    missing = []
    if not name:
        missing.append("商品名称(name)")
    if not category_id:
        missing.append("类别编号(category_id)，现有类别：C001电子产品 C002办公用品 C003食品饮料 C004生活用品")
    if missing:
        return json.dumps({"complete": False, "missing": missing,
                           "hint": "请提供商品名称和类别编号"}, ensure_ascii=False)
    pid = product_id or _next_id(db, "Product", "P")
    exists = db.execute(text("SELECT COUNT(*) FROM Product WHERE ProductID = :id"), {"id": pid}).scalar()
    if exists:
        pid = _next_id(db, "Product", "P")
    try:
        db.execute(text("INSERT INTO Product (ProductID, ProductName, CategoryID, Spec, Unit, Remark) VALUES (:id, :n, :c, :s, :u, :r)"),
                   {"id": pid, "n": name, "c": category_id or None,
                    "s": spec or None, "u": unit or None, "r": remark or None})
        db.commit()
        return json.dumps({"complete": True, "success": True, "id": pid,
                           "message": f"商品 {pid}({name}) 创建成功"}, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        return json.dumps({"complete": False, "success": False, "error": str(e)}, ensure_ascii=False)
