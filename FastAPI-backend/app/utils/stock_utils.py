from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict, Any
from ..models import TotalStock, WarehouseStock, BatchStock, PurchaseDetail, SaleDetail, SaleOutBatch
from ..database import engine


def update_stock_on_purchase_in(db: Session, warehouse_id: str, details: list, now: datetime):
    """采购入库：更新TotalStock、WarehouseStock、BatchStock"""
    for d in details:
        pid = d.ProductID
        qty = d.Quantity
        price = d.UnitPrice

        # 更新/创建 TotalStock
        ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
        if ts:
            old_total = ts.TotalQuantity
            old_amount = old_total * ts.AveragePrice if old_total > 0 else 0
            new_total = old_total + qty
            new_amount = old_amount + qty * price
            ts.TotalQuantity = new_total
            ts.AveragePrice = round(new_amount / new_total, 2) if new_total > 0 else 0
            ts.LastPurchasePrice = price
            ts.LastUpdated = now
        else:
            ts = TotalStock(
                ProductID=pid, TotalQuantity=qty, AveragePrice=price,
                LastPurchasePrice=price, LastUpdated=now
            )
            db.add(ts)

        # 更新/创建 WarehouseStock
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()
        if ws:
            ws.Quantity += qty
            ws.LastUpdated = now
        else:
            ws = WarehouseStock(
                ProductID=pid, WarehouseID=warehouse_id,
                Quantity=qty, LastUpdated=now
            )
            db.add(ws)

        # 创建 BatchStock（FIFO批次）
        import random
        batch = BatchStock(
            BatchID=f"BT{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}",
            ProductID=pid, WarehouseID=warehouse_id,
            PurchaseDetailID=d.PurchaseDetailID,
            Quantity=qty, RemainingQty=qty,
            UnitPrice=price, InDate=now
        )
        db.add(batch)


def rollback_stock_on_purchase_in(db: Session, warehouse_id: str, details: list, now: datetime):
    """采购入库回退：回退库存、删除BatchStock。如果商品全量回退则均价归零"""
    for d in details:
        pid = d.ProductID
        qty = d.Quantity

        # 回退 TotalStock
        ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
        if ts:
            ts.TotalQuantity -= qty
            if ts.TotalQuantity <= 0:
                ts.TotalQuantity = 0
                ts.AveragePrice = 0  # 全部回退时均价归零
            # 注意：如果还有库存，均价保持不变（因为总成本减少了，但减少的不是按均价计算的）
            ts.LastUpdated = now

        # 回退 WarehouseStock
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()
        if ws:
            ws.Quantity -= qty
            if ws.Quantity < 0:
                ws.Quantity = 0
            ws.LastUpdated = now

        # 删除该批次的 BatchStock（按 PurchaseDetailID 精确匹配）
        batches = db.query(BatchStock).filter(
            BatchStock.ProductID == pid,
            BatchStock.WarehouseID == warehouse_id,
            BatchStock.PurchaseDetailID == d.PurchaseDetailID
        ).all()
        for batch in batches:
            db.delete(batch)


def check_stock_sufficiency(db: Session, warehouse_id: str, details: list) -> list:
    """检查仓库库存是否充足，返回不足的商品列表"""
    insufficient = []
    for d in details:
        pid = d.ProductID
        qty = d.Quantity

        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()

        available = ws.Quantity if ws else 0
        if available < qty:
            # 获取商品名称
            from ..models import Product
            product = db.query(Product).filter(Product.ProductID == pid).first()
            insufficient.append({
                "ProductID": pid,
                "ProductName": product.ProductName if product else pid,
                "NeedQty": qty,
                "AvailableQty": available,
                "DiffQty": qty - available
            })

    return insufficient


def update_stock_on_sale_out(db: Session, warehouse_id: str, details: list, now: datetime):
    """销售出库：FIFO扣减BatchStock + 更新WarehouseStock + 更新TotalStock + 记录SaleOutBatch"""
    import random
    for d in details:
        pid = d.ProductID
        qty = d.Quantity

        # FIFO 扣减 BatchStock 并获取消耗明细（用于SaleOutBatch记录）
        batch_records = fifo_deduct_with_detail(db, pid, warehouse_id, qty)
        
        # 记录 SaleOutBatch（FIFO成本核算的关键数据）
        for br in batch_records:
            sob = SaleOutBatch(
                SaleOutBatchID=f"SOB{d.SaleDetailID}{random.randint(100,999)}",
                SaleDetailID=d.SaleDetailID,
                BatchID=br['BatchID'],
                Quantity=br['Quantity'],
                UnitPrice=br['UnitPrice'],
                OutDate=now
            )
            db.add(sob)

        # 更新 WarehouseStock
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()
        if ws:
            ws.Quantity -= qty
            if ws.Quantity < 0:
                ws.Quantity = 0
            ws.LastUpdated = now

        # 更新 TotalStock（只减数量，不改均价）
        ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
        if ts:
            ts.TotalQuantity -= qty
            if ts.TotalQuantity < 0:
                ts.TotalQuantity = 0
            ts.LastUpdated = now


def rollback_stock_on_sale_out(db: Session, warehouse_id: str, details: list, now: datetime):
    """销售出库回退：FIFO恢复BatchStock + 恢复WarehouseStock + 恢复TotalStock"""
    for d in details:
        pid = d.ProductID
        qty = d.Quantity

        # FIFO 恢复 BatchStock（加回到最早的批次）
        fifo_restore(db, pid, warehouse_id, qty)

        # 恢复 WarehouseStock
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()
        if ws:
            ws.Quantity += qty
            ws.LastUpdated = now
        else:
            ws = WarehouseStock(
                ProductID=pid, WarehouseID=warehouse_id,
                Quantity=qty, LastUpdated=now
            )
            db.add(ws)

        # 恢复 TotalStock
        ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
        if ts:
            ts.TotalQuantity += qty
            ts.LastUpdated = now
        else:
            # 极端情况：被删除了，重新创建
            ts = TotalStock(
                ProductID=pid, TotalQuantity=qty,
                AveragePrice=0, LastPurchasePrice=0, LastUpdated=now
            )
            db.add(ts)


def fifo_deduct(db: Session, product_id: str, warehouse_id: str, quantity: float):
    """FIFO方式从BatchStock中扣减指定数量"""
    remaining = quantity
    batches = db.query(BatchStock).filter(
        BatchStock.ProductID == product_id,
        BatchStock.WarehouseID == warehouse_id,
        BatchStock.RemainingQty > 0
    ).order_by(BatchStock.InDate.asc()).all()

    for batch in batches:
        if remaining <= 0:
            break
        if batch.RemainingQty >= remaining:
            batch.RemainingQty -= remaining
            remaining = 0
        else:
            remaining -= batch.RemainingQty
            batch.RemainingQty = 0


def fifo_restore(db: Session, product_id: str, warehouse_id: str, quantity: float):
    """FIFO方式恢复BatchStock（加回到最早的批次）"""
    remaining = quantity
    batches = db.query(BatchStock).filter(
        BatchStock.ProductID == product_id,
        BatchStock.WarehouseID == warehouse_id
    ).order_by(BatchStock.InDate.asc()).all()

    # 找到最早的批次进行恢复
    for batch in batches:
        if remaining <= 0:
            break
        # 恢复 RemainingQty（不超过原始 Quantity）
        can_restore = batch.Quantity - batch.RemainingQty
        if can_restore >= remaining:
            batch.RemainingQty += remaining
            remaining = 0
        else:
            batch.RemainingQty = batch.Quantity
            remaining -= can_restore

    # 如果所有批次都满了还余量，创建新批次
    if remaining > 0:
        batch = BatchStock(
            ProductID=product_id, WarehouseID=warehouse_id,
            Quantity=remaining, RemainingQty=remaining,
            UnitPrice=0, InDate=datetime.now()
        )
        db.add(batch)
