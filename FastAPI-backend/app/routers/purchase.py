from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models import PurchaseOrder, PurchaseDetail, Product
from ..schemas import (
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderOut,
    PurchaseDetailOut, PurchaseOrderFullOut, PurchaseDetailItem
)
from ..utils.stock_utils import update_stock_on_purchase_in, rollback_stock_on_purchase_in

router = APIRouter(prefix="/api/purchases", tags=["采购单"])


# ==================== 采购单 CRUD ====================
@router.get("/", response_model=List[PurchaseOrderFullOut])
def list_purchases(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseOrder)
    if status:
        query = query.filter(PurchaseOrder.Status == status)
    if supplier_id:
        query = query.filter(PurchaseOrder.SupplierID == supplier_id)
    orders = query.order_by(PurchaseOrder.OrderDate.desc()).all()

    # 批量预加载供应商名和仓库名（避免 N+1 查询）
    supplier_ids = list(set(o.SupplierID for o in orders))
    wh_ids = list(set(o.WarehouseID for o in orders))

    supplier_map = {}
    if supplier_ids:
        rows = db.execute(text("SELECT SupplierID, SupplierName FROM Supplier WHERE SupplierID IN :ids"),
                          {"ids": tuple(supplier_ids)}).mappings().all()
        supplier_map = {r["SupplierID"]: r["SupplierName"] for r in rows}

    wh_map = {}
    if wh_ids:
        rows = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseID IN :ids"),
                          {"ids": tuple(wh_ids)}).mappings().all()
        wh_map = {r["WarehouseID"]: r["WarehouseName"] for r in rows}

    result = []
    for o in orders:
        details = db.query(PurchaseDetail).filter(PurchaseDetail.PurchaseID == o.PurchaseID).all()
        supplier_name = supplier_map.get(o.SupplierID)
        wh_name = wh_map.get(o.WarehouseID)
        result.append(PurchaseOrderFullOut(
            PurchaseID=o.PurchaseID, SupplierID=o.SupplierID, WarehouseID=o.WarehouseID,
            OrderDate=o.OrderDate, Status=o.Status, TotalAmount=float(o.TotalAmount or 0),
            Operator=o.Operator, InDate=o.InDate, InOperator=o.InOperator,
            RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
            SupplierName=supplier_name, WarehouseName=wh_name,
            Details=[PurchaseDetailOut.model_validate(d) for d in details],
        ))
    return result


@router.get("/{purchase_id}", response_model=PurchaseOrderFullOut)
def get_purchase(purchase_id: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    details = db.query(PurchaseDetail).filter(PurchaseDetail.PurchaseID == purchase_id).all()
    supplier_name = db.execute(
        text("SELECT SupplierName FROM Supplier WHERE SupplierID = :sid"), {"sid": o.SupplierID}
    ).scalar()
    wh_name = db.execute(
        text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"), {"wid": o.WarehouseID}
    ).scalar()
    return PurchaseOrderFullOut(
        PurchaseID=o.PurchaseID, SupplierID=o.SupplierID, WarehouseID=o.WarehouseID,
        OrderDate=o.OrderDate, Status=o.Status, TotalAmount=float(o.TotalAmount or 0),
        Operator=o.Operator, InDate=o.InDate, InOperator=o.InOperator,
        RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
        SupplierName=supplier_name, WarehouseName=wh_name,
        Details=[PurchaseDetailOut.model_validate(d) for d in details],
    )


@router.post("/", response_model=PurchaseOrderOut)
def create_purchase(data: PurchaseOrderCreate, db: Session = Depends(get_db)):
    if db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == data.PurchaseID).first():
        raise HTTPException(status_code=400, detail="采购单编号已存在")

    total = sum(d.Amount for d in data.Details)
    order = PurchaseOrder(
        PurchaseID=data.PurchaseID, SupplierID=data.SupplierID,
        WarehouseID=data.WarehouseID, OrderDate=data.OrderDate or datetime.now(),
        Status="草稿", TotalAmount=total, Operator=data.Operator,
    )
    db.add(order)
    db.flush()  # 先提交主表，确保外键约束通过

    for item in data.Details:
        db.add(PurchaseDetail(
            PurchaseDetailID=item.PurchaseDetailID, PurchaseID=data.PurchaseID,
            ProductID=item.ProductID, Quantity=item.Quantity,
            UnitPrice=item.UnitPrice, Amount=item.Amount,
        ))

    db.commit()
    db.refresh(order)
    return order


@router.put("/{purchase_id}", response_model=PurchaseOrderOut)
def update_purchase(purchase_id: str, data: PurchaseOrderUpdate, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if o.Status == "已入库":
        raise HTTPException(status_code=400, detail="已入库的采购单不允许修改，请先执行入库回退")
    for key, val in data.model_dump(exclude_unset=True, exclude={'Details'}).items():
        setattr(o, key, val)

    # 如果传入了 Details，全删重建
    if data.Details is not None:
        # 删除旧明细
        old_details = db.query(PurchaseDetail).filter(PurchaseDetail.PurchaseID == purchase_id).all()
        for od in old_details:
            db.delete(od)
        db.flush()

        # 创建新明细
        total = 0
        for idx, item in enumerate(data.Details):
            detail = PurchaseDetail(
                PurchaseDetailID=f"PD{purchase_id}{str(idx+1).zfill(2)}",
                PurchaseID=purchase_id,
                ProductID=item.ProductID,
                Quantity=item.Quantity,
                UnitPrice=item.UnitPrice,
                Amount=item.Quantity * item.UnitPrice
            )
            total += detail.Amount
            db.add(detail)

        o.TotalAmount = total

    db.commit()
    db.refresh(o)
    return o


@router.delete("/{purchase_id}")
def delete_purchase(purchase_id: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if o.Status == "已入库":
        raise HTTPException(status_code=400, detail="已入库的采购单不允许删除，请先执行入库回退")
    db.query(PurchaseDetail).filter(PurchaseDetail.PurchaseID == purchase_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


# ==================== 采购明细管理 ====================
@router.post("/{purchase_id}/details", response_model=PurchaseDetailOut)
def add_purchase_detail(purchase_id: str, item: PurchaseDetailItem, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if o.Status == "已入库":
        raise HTTPException(status_code=400, detail="已入库的采购单不允许修改")

    detail = PurchaseDetail(
        PurchaseDetailID=item.PurchaseDetailID, PurchaseID=purchase_id,
        ProductID=item.ProductID, Quantity=item.Quantity,
        UnitPrice=item.UnitPrice, Amount=item.Amount,
    )
    db.add(detail)

    o.TotalAmount = float(o.TotalAmount or 0) + item.Amount
    db.commit()
    db.refresh(detail)
    return detail


@router.delete("/{purchase_id}/details/{detail_id}")
def remove_purchase_detail(purchase_id: str, detail_id: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if o.Status == "已入库":
        raise HTTPException(status_code=400, detail="已入库的采购单不允许修改")

    detail = db.query(PurchaseDetail).filter(
        PurchaseDetail.PurchaseDetailID == detail_id, PurchaseDetail.PurchaseID == purchase_id
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明细不存在")

    o.TotalAmount = float(o.TotalAmount or 0) - float(detail.Amount or 0)
    db.delete(detail)
    db.commit()
    return {"message": "删除成功"}


# ==================== 入库操作 ====================
@router.post("/{purchase_id}/in-stock")
def purchase_in_stock(purchase_id: str, operator: str = "系统", db: Session = Depends(get_db)):
    """整单入库：变更状态，更新库存"""
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if o.Status == "已入库":
        raise HTTPException(status_code=400, detail="采购单已入库")

    details = db.query(PurchaseDetail).filter(PurchaseDetail.PurchaseID == purchase_id).all()
    if not details:
        raise HTTPException(status_code=400, detail="采购单无明细，无法入库")

    # 使用 stock_utils 更新库存
    now = datetime.now()
    try:
        update_stock_on_purchase_in(db, o.WarehouseID, details, now)

        # 更新采购单状态
        o.Status = "已入库"
        o.InDate = now
        o.InOperator = operator

        db.commit()
        return {"message": "入库成功", "status": "已入库"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"入库失败：{str(e)}")


# ==================== 入库回退 ====================
@router.post("/{purchase_id}/in-stock-rollback")
def purchase_in_stock_rollback(purchase_id: str, operator: str = "系统", db: Session = Depends(get_db)):
    """入库回退：将已入库采购单回退，同时回退所有库存"""
    o = db.query(PurchaseOrder).filter(PurchaseOrder.PurchaseID == purchase_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if o.Status != "已入库":
        raise HTTPException(status_code=400, detail="只有已入库的采购单才能执行入库回退")

    now = datetime.now()
    details = db.query(PurchaseDetail).filter(PurchaseDetail.PurchaseID == purchase_id).all()

    rollback_stock_on_purchase_in(db, o.WarehouseID, details, now)

    o.Status = "已回退"
    o.RollbackDate = now
    o.RollbackOperator = operator
    db.commit()
    db.refresh(o)
    return o
