from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models import TransferOrder, TransferDetail, WarehouseStock
from ..schemas import (
    TransferOrderCreate, TransferOrderUpdate, TransferOrderOut,
    TransferDetailOut, TransferOrderFullOut, TransferDetailItem
)

router = APIRouter(prefix="/api/transfers", tags=["调拨单"])


# ==================== 调拨单 CRUD ====================
@router.get("/", response_model=List[TransferOrderFullOut])
def list_transfers(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TransferOrder)
    if status:
        query = query.filter(TransferOrder.Status == status)
    orders = query.order_by(TransferOrder.OrderDate.desc()).all()

    result = []
    for o in orders:
        details = db.query(TransferDetail).filter(TransferDetail.TransferID == o.TransferID).all()
        from_wh = db.execute(text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
                             {"wid": o.FromWarehouseID}).scalar()
        to_wh = db.execute(text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
                           {"wid": o.ToWarehouseID}).scalar()
        result.append(TransferOrderFullOut(
            TransferID=o.TransferID, FromWarehouseID=o.FromWarehouseID,
            ToWarehouseID=o.ToWarehouseID, OrderDate=o.OrderDate,
            Status=o.Status, Operator=o.Operator,
            FromWarehouseName=from_wh, ToWarehouseName=to_wh,
            Details=[TransferDetailOut.model_validate(d) for d in details],
        ))
    return result


@router.get("/{transfer_id}", response_model=TransferOrderFullOut)
def get_transfer(transfer_id: str, db: Session = Depends(get_db)):
    o = db.query(TransferOrder).filter(TransferOrder.TransferID == transfer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    details = db.query(TransferDetail).filter(TransferDetail.TransferID == transfer_id).all()
    from_wh = db.execute(text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
                         {"wid": o.FromWarehouseID}).scalar()
    to_wh = db.execute(text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
                       {"wid": o.ToWarehouseID}).scalar()
    return TransferOrderFullOut(
        TransferID=o.TransferID, FromWarehouseID=o.FromWarehouseID,
        ToWarehouseID=o.ToWarehouseID, OrderDate=o.OrderDate,
        Status=o.Status, Operator=o.Operator,
        FromWarehouseName=from_wh, ToWarehouseName=to_wh,
        Details=[TransferDetailOut.model_validate(d) for d in details],
    )


@router.post("/", response_model=TransferOrderOut)
def create_transfer(data: TransferOrderCreate, db: Session = Depends(get_db)):
    if db.query(TransferOrder).filter(TransferOrder.TransferID == data.TransferID).first():
        raise HTTPException(status_code=400, detail="调拨单编号已存在")

    if data.FromWarehouseID == data.ToWarehouseID:
        raise HTTPException(status_code=400, detail="调入仓库和调出仓库不能相同")

    order = TransferOrder(
        TransferID=data.TransferID, FromWarehouseID=data.FromWarehouseID,
        ToWarehouseID=data.ToWarehouseID, OrderDate=data.OrderDate or datetime.now(),
        Status="草稿", Operator=data.Operator,
    )
    db.add(order)
    db.flush()  # 先提交主表，确保外键约束通过

    for item in data.Details:
        db.add(TransferDetail(
            TransferDetailID=item.TransferDetailID, TransferID=data.TransferID,
            ProductID=item.ProductID, Quantity=item.Quantity,
        ))

    db.commit()
    db.refresh(order)
    return order


@router.put("/{transfer_id}", response_model=TransferOrderOut)
def update_transfer(transfer_id: str, data: TransferOrderUpdate, db: Session = Depends(get_db)):
    o = db.query(TransferOrder).filter(TransferOrder.TransferID == transfer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="非草稿状态不允许修改")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(o, key, val)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/{transfer_id}")
def delete_transfer(transfer_id: str, db: Session = Depends(get_db)):
    o = db.query(TransferOrder).filter(TransferOrder.TransferID == transfer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="非草稿状态不允许删除")
    db.query(TransferDetail).filter(TransferDetail.TransferID == transfer_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


# ==================== 审核操作（同步出入库）====================
@router.post("/{transfer_id}/approve")
def approve_transfer(transfer_id: str, db: Session = Depends(get_db)):
    """调拨单审核：调出仓库出库 + 调入仓库入库，总库存不变"""
    o = db.query(TransferOrder).filter(TransferOrder.TransferID == transfer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态可审核")

    details = db.query(TransferDetail).filter(TransferDetail.TransferID == transfer_id).all()
    if not details:
        raise HTTPException(status_code=400, detail="调拨单无明细")

    now = datetime.now()

    # 先检查调出仓库库存是否充足
    insufficient = []
    for d in details:
        ws = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == d.ProductID,
            WarehouseStock.WarehouseID == o.FromWarehouseID,
        ).first()
        available = float(ws.Quantity) if ws else 0
        if available < float(d.Quantity):
            name = db.execute(text("SELECT ProductName FROM Product WHERE ProductID = :pid"),
                              {"pid": d.ProductID}).scalar()
            insufficient.append({"ProductID": d.ProductID, "ProductName": name,
                                 "Need": float(d.Quantity), "Available": available})

    if insufficient:
        return {"success": False, "message": "调出仓库库存不足", "insufficient": insufficient}

    for d in details:
        # 调出仓库出库
        ws_from = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == d.ProductID,
            WarehouseStock.WarehouseID == o.FromWarehouseID,
        ).first()
        if ws_from:
            ws_from.Quantity = float(ws_from.Quantity or 0) - float(d.Quantity)
            ws_from.LastUpdated = now

        # 调入仓库入库
        ws_to = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == d.ProductID,
            WarehouseStock.WarehouseID == o.ToWarehouseID,
        ).first()
        if ws_to:
            ws_to.Quantity = float(ws_to.Quantity or 0) + float(d.Quantity)
            ws_to.LastUpdated = now
        else:
            db.add(WarehouseStock(
                ProductID=d.ProductID, WarehouseID=o.ToWarehouseID,
                Quantity=d.Quantity, LastUpdated=now,
            ))

        # 更新批次库存：从调出仓库的批次中扣减
        need_qty = float(d.Quantity)
        batches = db.execute(text(
            "SELECT BatchID, RemainingQty FROM BatchStock "
            "WHERE ProductID = :pid AND WarehouseID = :wid AND RemainingQty > 0 "
            "ORDER BY InDate ASC"
        ), {"pid": d.ProductID, "wid": o.FromWarehouseID}).mappings().all()

        for batch in batches:
            if need_qty <= 0:
                break
            remaining = float(batch["RemainingQty"])
            deduct = min(remaining, need_qty)
            db.execute(text(
                "UPDATE BatchStock SET RemainingQty = RemainingQty - :dq WHERE BatchID = :bid"
            ), {"dq": deduct, "bid": batch["BatchID"]})

            # 为目标仓库创建对应 BatchStock（带相同单价）
            price_row = db.execute(text("SELECT UnitPrice FROM BatchStock WHERE BatchID = :bid"),
                                   {"bid": batch["BatchID"]}).mappings().first()
            unit_price = float(price_row["UnitPrice"]) if price_row else 0

            import random
            db.execute(text(
                "INSERT INTO BatchStock (BatchID, ProductID, WarehouseID, PurchaseDetailID, InDate, UnitPrice, RemainingQty, Quantity) "
                "VALUES (:bid, :pid, :wid, NULL, :dt, :up, :qty, :qty)"
            ), {
                "bid": f"TR{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}",
                "pid": d.ProductID, "wid": o.ToWarehouseID,
                "dt": now, "up": unit_price, "qty": deduct
            })
            need_qty -= deduct

    o.Status = "已审核"
    db.commit()
    return {"message": "审核通过，出入库同步完成", "status": "已审核"}


# ==================== 审核回退（同步出入库回退）====================
@router.post("/{transfer_id}/approve-rollback")
def rollback_transfer(transfer_id: str, db: Session = Depends(get_db)):
    """审核回退：调出仓库入库 + 调入仓库出库"""
    o = db.query(TransferOrder).filter(TransferOrder.TransferID == transfer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    if o.Status != "已审核":
        raise HTTPException(status_code=400, detail="只有已审核状态可回退")

    details = db.query(TransferDetail).filter(TransferDetail.TransferID == transfer_id).all()
    now = datetime.now()

    for d in details:
        # 调出仓库回退（加回来）
        ws_from = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == d.ProductID,
            WarehouseStock.WarehouseID == o.FromWarehouseID,
        ).first()
        if ws_from:
            ws_from.Quantity = float(ws_from.Quantity or 0) + float(d.Quantity)
            ws_from.LastUpdated = now

        # 调入仓库回退（减回去）
        ws_to = db.query(WarehouseStock).filter(
            WarehouseStock.ProductID == d.ProductID,
            WarehouseStock.WarehouseID == o.ToWarehouseID,
        ).first()
        if ws_to:
            ws_to.Quantity = float(ws_to.Quantity or 0) - float(d.Quantity)
            ws_to.LastUpdated = now

    o.Status = "已回退"
    db.commit()
    return {"message": "审核回退成功，出入库同步回退完成", "status": "已回退"}
