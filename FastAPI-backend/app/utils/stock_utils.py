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


def fifo_deduct_with_detail(db: Session, product_id: str, warehouse_id: str, quantity: float) -> List[Dict]:
    """FIFO扣减BatchStock并返回扣减明细
    
    返回: [{"BatchID": str, "Quantity": float, "UnitPrice": float}, ...]
    """
    remaining = quantity
    batches = db.query(BatchStock).filter(
        BatchStock.ProductID == product_id,
        BatchStock.WarehouseID == warehouse_id,
        BatchStock.RemainingQty > 0
    ).order_by(BatchStock.InDate.asc()).all()

    result = []
    for batch in batches:
        if remaining <= 0:
            break
        if batch.RemainingQty >= remaining:
            result.append({
                "BatchID": batch.BatchID,
                "Quantity": remaining,
                "UnitPrice": float(batch.UnitPrice)
            })
            batch.RemainingQty -= remaining
            remaining = 0
        else:
            result.append({
                "BatchID": batch.BatchID,
                "Quantity": float(batch.RemainingQty),
                "UnitPrice": float(batch.UnitPrice)
            })
            remaining -= batch.RemainingQty
            batch.RemainingQty = 0

    return result


def apply_purchase_return(db: Session, warehouse_id: str, details: list, now: datetime):
    """采购退货：按原批次精确扣减BatchStock + 扣减WarehouseStock/TotalStock
    
    details: list of dicts with keys PurchaseDetailID, ProductID, Quantity, UnitPrice
    """
    for d in details:
        pid = d["ProductID"]
        qty = d["Quantity"]
        pdetail_id = d["PurchaseDetailID"]

        # 按入库时间升序扣减BatchStock（同PurchaseDetailID的批次）
        remaining = qty
        batches = db.query(BatchStock).filter(
            BatchStock.ProductID == pid,
            BatchStock.WarehouseID == warehouse_id,
            BatchStock.PurchaseDetailID == pdetail_id,
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

        # 扣减 WarehouseStock
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()
        if ws:
            ws.Quantity -= qty
            if ws.Quantity < 0:
                ws.Quantity = 0
            ws.LastUpdated = now

        # 扣减 TotalStock（均价不变）
        ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
        if ts:
            ts.TotalQuantity -= qty
            if ts.TotalQuantity < 0:
                ts.TotalQuantity = 0
            ts.LastUpdated = now


def rollback_purchase_return(db: Session, return_id: str, warehouse_id: str, details: list, now: datetime):
    """采购退货回退：恢复BatchStock + 恢复WarehouseStock/TotalStock
    
    details: list of dicts with keys PurchaseDetailID, ProductID, Quantity, UnitPrice
    """
    for d in details:
        pid = d["ProductID"]
        qty = d["Quantity"]
        pdetail_id = d["PurchaseDetailID"]
        price = d["UnitPrice"]

        # 恢复 BatchStock（按 PurchaseDetailID 精确匹配，加回到相应批次）
        remaining = qty
        batches = db.query(BatchStock).filter(
            BatchStock.ProductID == pid,
            BatchStock.WarehouseID == warehouse_id,
            BatchStock.PurchaseDetailID == pdetail_id
        ).order_by(BatchStock.InDate.asc()).all()

        for batch in batches:
            if remaining <= 0:
                break
            can_restore = float(batch.Quantity) - float(batch.RemainingQty)
            if can_restore >= remaining:
                batch.RemainingQty += remaining
                remaining = 0
            else:
                batch.RemainingQty = batch.Quantity
                remaining -= can_restore

        # 如果还有余量，创建批次记录
        if remaining > 0:
            import random
            new_batch = BatchStock(
                BatchID=f"BTPR{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}",
                ProductID=pid, WarehouseID=warehouse_id,
                PurchaseDetailID=pdetail_id,
                Quantity=remaining, RemainingQty=remaining,
                UnitPrice=price, InDate=now
            )
            db.add(new_batch)

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
            ts = TotalStock(
                ProductID=pid, TotalQuantity=qty,
                AveragePrice=price, LastUpdated=now
            )
            db.add(ts)


def apply_sale_return(db: Session, warehouse_id: str, details: list, now: datetime):
    """销售退货：按SaleOutBatch原路恢复BatchStock + 恢复WarehouseStock/TotalStock
    
    details: list of SaleDetail-like objects (with SaleDetailID, ProductID, Quantity, UnitPrice)
    """
    for d in details:
        pid = d["ProductID"]
        qty = d["Quantity"]
        sale_detail_id = d["SaleDetailID"]

        # 查询 SaleOutBatch 找到当时扣了哪些批次
        sob_records = db.query(SaleOutBatch).filter(
            SaleOutBatch.SaleDetailID == sale_detail_id
        ).order_by(SaleOutBatch.OutDate.asc()).all()

        remaining = qty
        for sob in sob_records:
            if remaining <= 0:
                break
            # 恢复 BatchStock.RemainingQty（不超过原始 Quantity）
            batch = db.query(BatchStock).filter(
                BatchStock.BatchID == sob.BatchID
            ).first()
            if not batch:
                continue
            can_restore = min(float(sob.Quantity), remaining)
            # 确保不超过原始 Quantity
            max_restore = float(batch.Quantity) - float(batch.RemainingQty)
            if max_restore < can_restore:
                can_restore = max_restore
            if can_restore > 0:
                batch.RemainingQty += can_restore
                remaining -= can_restore

        # 如果所有批次都满了还余量，创建新批次
        if remaining > 0:
            import random
            new_batch = BatchStock(
                BatchID=f"BTSR{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}",
                ProductID=pid, WarehouseID=warehouse_id,
                Quantity=remaining, RemainingQty=remaining,
                UnitPrice=d["UnitPrice"], InDate=now
            )
            db.add(new_batch)

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
            ts = TotalStock(
                ProductID=pid, TotalQuantity=qty,
                AveragePrice=d["UnitPrice"], LastUpdated=now
            )
            db.add(ts)


def rollback_sale_return(db: Session, return_id: str, warehouse_id: str, details: list, now: datetime):
    """销售退货回退：反向扣减BatchStock + 扣减WarehouseStock/TotalStock
    
    details: list of dicts with keys SaleDetailID, ProductID, Quantity, UnitPrice
    """
    for d in details:
        pid = d["ProductID"]
        qty = d["Quantity"]
        sale_detail_id = d["SaleDetailID"]

        # 按 SaleOutBatch 记录，恢复时反向扣减
        sob_records = db.query(SaleOutBatch).filter(
            SaleOutBatch.SaleDetailID == sale_detail_id
        ).order_by(SaleOutBatch.OutDate.desc()).all()

        remaining = qty
        for sob in sob_records:
            if remaining <= 0:
                break
            batch = db.query(BatchStock).filter(
                BatchStock.BatchID == sob.BatchID
            ).first()
            if not batch:
                continue
            deduct = min(float(sob.Quantity), remaining, float(batch.RemainingQty))
            if deduct > 0:
                batch.RemainingQty -= deduct
                remaining -= deduct

        # 扣减 WarehouseStock
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == pid,
            WarehouseStock.WarehouseID == warehouse_id
        ).first()
        if ws:
            ws.Quantity -= qty
            if ws.Quantity < 0:
                ws.Quantity = 0
            ws.LastUpdated = now

        # 扣减 TotalStock
        ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
        if ts:
            ts.TotalQuantity -= qty
            if ts.TotalQuantity < 0:
                ts.TotalQuantity = 0
            ts.LastUpdated = now


def apply_profit_loss(db: Session, warehouse_id: str, pl_details: list, now: datetime):
    """损益单审核：
    盘盈（Quantity>0）：创建新BatchStock + 增加 WarehouseStock + 增加 TotalStock + 更新均价
    盘亏（Quantity<0）：FIFO 扣减 BatchStock + 扣减 WarehouseStock + 扣减 TotalStock
    
    pl_details: list of dicts with keys ProductID, Quantity, UnitPrice, ProfitLossDetailID
    """
    import random
    for d in pl_details:
        pid = d["ProductID"]
        qty = d["Quantity"]
        price = d["UnitPrice"]

        if qty > 0:
            # 盘盈：创建新BatchStock
            batch = BatchStock(
                BatchID=f"BTPL{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}",
                ProductID=pid, WarehouseID=warehouse_id,
                Quantity=qty, RemainingQty=qty,
                UnitPrice=price, InDate=now
            )
            db.add(batch)

            # 增加 WarehouseStock
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

            # 增加 TotalStock 并更新均价
            ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
            if ts:
                old_total = float(ts.TotalQuantity)
                old_amount = old_total * float(ts.AveragePrice) if old_total > 0 else 0
                new_total = old_total + qty
                new_amount = old_amount + qty * price
                ts.TotalQuantity = new_total
                ts.AveragePrice = round(new_amount / new_total, 2) if new_total > 0 else 0
                ts.LastUpdated = now
            else:
                ts = TotalStock(
                    ProductID=pid, TotalQuantity=qty,
                    AveragePrice=price, LastUpdated=now
                )
                db.add(ts)

        elif qty < 0:
            # 盘亏：FIFO 扣减
            abs_qty = abs(qty)
            fifo_deduct(db, pid, warehouse_id, abs_qty)

            # 扣减 WarehouseStock
            ws = db.query(WarehouseStock).filter(
                WarehouseStock.ProductID == pid,
                WarehouseStock.WarehouseID == warehouse_id
            ).first()
            if ws:
                ws.Quantity -= abs_qty
                if ws.Quantity < 0:
                    ws.Quantity = 0
                ws.LastUpdated = now

            # 扣减 TotalStock（均价不变）
            ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
            if ts:
                ts.TotalQuantity -= abs_qty
                if ts.TotalQuantity < 0:
                    ts.TotalQuantity = 0
                ts.LastUpdated = now


def rollback_profit_loss(db: Session, pl_id: str, warehouse_id: str, pl_details: list, now: datetime):
    """损益回退：反向操作
    盘盈（Quantity>0）：反向扣减 BatchStock + WarehouseStock + TotalStock
    盘亏（Quantity<0）：反向恢复 BatchStock + WarehouseStock + TotalStock
    """
    for d in pl_details:
        pid = d["ProductID"]
        qty = d["Quantity"]
        price = d["UnitPrice"]

        if qty > 0:
            # 反转盘盈 → 扣减
            abs_qty = qty
            fifo_deduct(db, pid, warehouse_id, abs_qty)

            ws = db.query(WarehouseStock).filter(
                WarehouseStock.ProductID == pid,
                WarehouseStock.WarehouseID == warehouse_id
            ).first()
            if ws:
                ws.Quantity -= abs_qty
                if ws.Quantity < 0:
                    ws.Quantity = 0
                ws.LastUpdated = now

            ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
            if ts:
                old_total = float(ts.TotalQuantity)
                old_amount = old_total * float(ts.AveragePrice) if old_total > 0 else 0
                new_total = old_total - abs_qty
                ts.TotalQuantity = new_total
                ts.AveragePrice = round((old_amount - abs_qty * price) / new_total, 2) if new_total > 0 else 0
                ts.LastUpdated = now

        elif qty < 0:
            # 反转盘亏 → 恢复
            abs_qty = abs(qty)
            import random
            batch = BatchStock(
                BatchID=f"BTRL{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}",
                ProductID=pid, WarehouseID=warehouse_id,
                Quantity=abs_qty, RemainingQty=abs_qty,
                UnitPrice=price, InDate=now
            )
            db.add(batch)

            ws = db.query(WarehouseStock).filter(
                WarehouseStock.ProductID == pid,
                WarehouseStock.WarehouseID == warehouse_id
            ).first()
            if ws:
                ws.Quantity += abs_qty
                ws.LastUpdated = now
            else:
                ws = WarehouseStock(
                    ProductID=pid, WarehouseID=warehouse_id,
                    Quantity=abs_qty, LastUpdated=now
                )
                db.add(ws)

            ts = db.query(TotalStock).filter(TotalStock.ProductID == pid).first()
            if ts:
                old_total = float(ts.TotalQuantity)
                old_amount = old_total * float(ts.AveragePrice) if old_total > 0 else 0
                new_total = old_total + abs_qty
                new_amount = old_amount + abs_qty * price
                ts.TotalQuantity = new_total
                ts.AveragePrice = round(new_amount / new_total, 2) if new_total > 0 else 0
                ts.LastUpdated = now
            else:
                ts = TotalStock(
                    ProductID=pid, TotalQuantity=abs_qty,
                    AveragePrice=price, LastUpdated=now
                )
                db.add(ts)
