from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models import SaleOrder, SaleDetail
from ..schemas import (
    SaleOrderCreate, SaleOrderUpdate, SaleOrderOut,
    SaleDetailOut, SaleOrderFullOut, SaleDetailItem
)
from ..utils.stock_utils import check_stock_sufficiency, update_stock_on_sale_out, rollback_stock_on_sale_out

router = APIRouter(prefix="/api/sales", tags=["销售单"])


# ==================== 销售单 CRUD ====================
@router.get("/", response_model=List[SaleOrderFullOut])
def list_sales(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(SaleOrder)
    if status:
        query = query.filter(SaleOrder.Status == status)
    if customer_id:
        query = query.filter(SaleOrder.CustomerID == customer_id)
    orders = query.order_by(SaleOrder.OrderDate.desc()).all()

    # 批量预加载客户名和仓库名（避免 N+1 查询）
    customer_ids = list(set(o.CustomerID for o in orders))
    wh_ids = list(set(o.WarehouseID for o in orders))

    customer_map = {}
    if customer_ids:
        rows = db.execute(text("SELECT CustomerID, CustomerName FROM Customer WHERE CustomerID IN :ids"),
                          {"ids": tuple(customer_ids)}).mappings().all()
        customer_map = {r["CustomerID"]: r["CustomerName"] for r in rows}

    wh_map = {}
    if wh_ids:
        rows = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseID IN :ids"),
                          {"ids": tuple(wh_ids)}).mappings().all()
        wh_map = {r["WarehouseID"]: r["WarehouseName"] for r in rows}

    result = []
    for o in orders:
        details = db.query(SaleDetail).filter(SaleDetail.SaleID == o.SaleID).all()
        customer_name = customer_map.get(o.CustomerID)
        wh_name = wh_map.get(o.WarehouseID)
        result.append(SaleOrderFullOut(
            SaleID=o.SaleID, CustomerID=o.CustomerID, WarehouseID=o.WarehouseID,
            OrderDate=o.OrderDate, Status=o.Status, TotalAmount=float(o.TotalAmount or 0),
            Operator=o.Operator, OutDate=o.OutDate, OutOperator=o.OutOperator,
            RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
            CustomerName=customer_name, WarehouseName=wh_name,
            Details=[SaleDetailOut.model_validate(d) for d in details],
        ))
    return result


@router.get("/{sale_id}", response_model=SaleOrderFullOut)
def get_sale(sale_id: str, db: Session = Depends(get_db)):
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    details = db.query(SaleDetail).filter(SaleDetail.SaleID == sale_id).all()
    customer_name = db.execute(
        text("SELECT CustomerName FROM Customer WHERE CustomerID = :cid"), {"cid": o.CustomerID}
    ).scalar()
    wh_name = db.execute(
        text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"), {"wid": o.WarehouseID}
    ).scalar()
    return SaleOrderFullOut(
        SaleID=o.SaleID, CustomerID=o.CustomerID, WarehouseID=o.WarehouseID,
        OrderDate=o.OrderDate, Status=o.Status, TotalAmount=float(o.TotalAmount or 0),
        Operator=o.Operator, OutDate=o.OutDate, OutOperator=o.OutOperator,
        RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
        CustomerName=customer_name, WarehouseName=wh_name,
        Details=[SaleDetailOut.model_validate(d) for d in details],
    )


@router.post("/", response_model=SaleOrderOut)
def create_sale(data: SaleOrderCreate, db: Session = Depends(get_db)):
    if db.query(SaleOrder).filter(SaleOrder.SaleID == data.SaleID).first():
        raise HTTPException(status_code=400, detail="销售单编号已存在")

    total = sum(d.Amount for d in data.Details)
    order = SaleOrder(
        SaleID=data.SaleID, CustomerID=data.CustomerID,
        WarehouseID=data.WarehouseID, OrderDate=data.OrderDate or datetime.now(),
        Status="草稿", TotalAmount=total, Operator=data.Operator,
    )
    db.add(order)
    db.flush()  # 先提交主表，确保外键约束通过

    for item in data.Details:
        db.add(SaleDetail(
            SaleDetailID=item.SaleDetailID, SaleID=data.SaleID,
            ProductID=item.ProductID, Quantity=item.Quantity,
            UnitPrice=item.UnitPrice, Amount=item.Amount,
        ))

    db.commit()
    db.refresh(order)
    return order


@router.put("/{sale_id}", response_model=SaleOrderOut)
def update_sale(sale_id: str, data: SaleOrderUpdate, db: Session = Depends(get_db)):
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    if o.Status == "已出库":
        raise HTTPException(status_code=400, detail="已出库的销售单不允许修改，请先执行出库回退")
    for key, val in data.model_dump(exclude_unset=True, exclude={'Details'}).items():
        setattr(o, key, val)

    # 如果传入了 Details，全删重建
    if data.Details is not None:
        # 删除旧明细
        old_details = db.query(SaleDetail).filter(SaleDetail.SaleID == sale_id).all()
        for od in old_details:
            db.delete(od)
        db.flush()

        # 创建新明细
        total = 0
        for idx, item in enumerate(data.Details):
            detail = SaleDetail(
                SaleDetailID=f"SD{sale_id}{str(idx+1).zfill(2)}",
                SaleID=sale_id,
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


@router.delete("/{sale_id}")
def delete_sale(sale_id: str, db: Session = Depends(get_db)):
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    if o.Status == "已出库":
        raise HTTPException(status_code=400, detail="已出库的销售单不允许删除，请先执行出库回退")
    db.query(SaleDetail).filter(SaleDetail.SaleID == sale_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


# ==================== 销售明细管理 ====================
@router.post("/{sale_id}/details", response_model=SaleDetailOut)
def add_sale_detail(sale_id: str, item: SaleDetailItem, db: Session = Depends(get_db)):
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    if o.Status == "已出库":
        raise HTTPException(status_code=400, detail="已出库的销售单不允许修改")

    detail = SaleDetail(
        SaleDetailID=item.SaleDetailID, SaleID=sale_id,
        ProductID=item.ProductID, Quantity=item.Quantity,
        UnitPrice=item.UnitPrice, Amount=item.Amount,
    )
    db.add(detail)

    o.TotalAmount = float(o.TotalAmount or 0) + item.Amount
    db.commit()
    db.refresh(detail)
    return detail


@router.delete("/{sale_id}/details/{detail_id}")
def remove_sale_detail(sale_id: str, detail_id: str, db: Session = Depends(get_db)):
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    if o.Status == "已出库":
        raise HTTPException(status_code=400, detail="已出库的销售单不允许修改")

    detail = db.query(SaleDetail).filter(
        SaleDetail.SaleDetailID == detail_id, SaleDetail.SaleID == sale_id
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明细不存在")

    o.TotalAmount = float(o.TotalAmount or 0) - float(detail.Amount or 0)
    db.delete(detail)
    db.commit()
    return {"message": "删除成功"}


# ==================== 出库操作 ====================
@router.post("/{sale_id}/out-stock")
def sale_out_stock(sale_id: str, operator: str = "系统", db: Session = Depends(get_db)):
    """整单出库：检查库存，变更状态，扣减库存（FIFO）"""
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    if o.Status == "已出库":
        raise HTTPException(status_code=400, detail="销售单已出库")

    details = db.query(SaleDetail).filter(SaleDetail.SaleID == sale_id).all()
    if not details:
        raise HTTPException(status_code=400, detail="销售单无明细，无法出库")

    # 检查库存
    insufficient = check_stock_sufficiency(db, o.WarehouseID, details)
    if insufficient:
        return {"success": False, "message": "库存不足", "insufficient_items": insufficient}

    # 执行出库
    now = datetime.now()
    try:
        update_stock_on_sale_out(db, o.WarehouseID, details, now)

        o.Status = "已出库"
        o.OutDate = now
        o.OutOperator = operator

        db.commit()
        db.refresh(o)
        return {"success": True, "data": o}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"出库失败：{str(e)}")


# ==================== 出库回退 ====================
@router.post("/{sale_id}/out-stock-rollback")
def sale_out_stock_rollback(sale_id: str, operator: str = "系统", db: Session = Depends(get_db)):
    """出库回退：将已出库销售单回退，同时回退所有库存"""
    o = db.query(SaleOrder).filter(SaleOrder.SaleID == sale_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售单不存在")
    if o.Status != "已出库":
        raise HTTPException(status_code=400, detail="只有已出库的销售单才能执行出库回退")

    now = datetime.now()
    details = db.query(SaleDetail).filter(SaleDetail.SaleID == sale_id).all()

    rollback_stock_on_sale_out(db, o.WarehouseID, details, now)

    o.Status = "已回退"
    o.RollbackDate = now
    o.RollbackOperator = operator
    db.commit()
    db.refresh(o)
    return {"success": True, "data": o}
