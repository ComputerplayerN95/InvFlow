from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models import (
    PurchaseReturnOrder, PurchaseReturnDetail, PurchaseOrder, PurchaseDetail,
    SaleReturnOrder, SaleReturnDetail, SaleOrder, SaleDetail,
    BatchStock, WarehouseStock, TotalStock, SaleOutBatch,
)
from ..schemas import (
    PurchaseReturnCreate, PurchaseReturnUpdate, PurchaseReturnOrderOut,
    PurchaseReturnDetailOut, PurchaseReturnOrderFullOut, PurchaseReturnDetailItem,
    SaleReturnCreate, SaleReturnUpdate, SaleReturnOrderOut,
    SaleReturnDetailOut, SaleReturnOrderFullOut, SaleReturnDetailItem,
    MessageResponse,
)
from ..utils.stock_utils import (
    apply_purchase_return as stock_apply_purchase_return,
    rollback_purchase_return as stock_rollback_purchase_return,
    apply_sale_return as stock_apply_sale_return,
    rollback_sale_return as stock_rollback_sale_return,
)

router = APIRouter(prefix="/api", tags=["退货管理"])


# ====================================================================
#  采购退货
# ====================================================================
purchase_return_router = APIRouter(prefix="/purchase-returns", tags=["采购退货"])


@purchase_return_router.get("/", response_model=List[PurchaseReturnOrderFullOut])
def list_purchase_returns(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseReturnOrder)
    if status:
        query = query.filter(PurchaseReturnOrder.Status == status)
    if supplier_id:
        query = query.filter(PurchaseReturnOrder.SupplierID == supplier_id)
    orders = query.order_by(PurchaseReturnOrder.ReturnDate.desc()).all()

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
        details = db.query(PurchaseReturnDetail).filter(
            PurchaseReturnDetail.ReturnID == o.ReturnID).all()
        result.append(PurchaseReturnOrderFullOut(
            ReturnID=o.ReturnID, PurchaseID=o.PurchaseID,
            SupplierID=o.SupplierID, WarehouseID=o.WarehouseID,
            ReturnDate=o.ReturnDate, Status=o.Status,
            TotalAmount=float(o.TotalAmount or 0),
            Operator=o.Operator, ReturnOperator=o.ReturnOperator,
            RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
            Remark=o.Remark,
            SupplierName=supplier_map.get(o.SupplierID),
            WarehouseName=wh_map.get(o.WarehouseID),
            Details=[PurchaseReturnDetailOut.model_validate(d) for d in details],
        ))
    return result


@purchase_return_router.get("/{return_id}", response_model=PurchaseReturnOrderFullOut)
def get_purchase_return(return_id: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseReturnOrder).filter(
        PurchaseReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购退货单不存在")
    details = db.query(PurchaseReturnDetail).filter(
        PurchaseReturnDetail.ReturnID == return_id).all()
    supplier_name = db.execute(
        text("SELECT SupplierName FROM Supplier WHERE SupplierID = :sid"),
        {"sid": o.SupplierID}).scalar()
    wh_name = db.execute(
        text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
        {"wid": o.WarehouseID}).scalar()
    return PurchaseReturnOrderFullOut(
        ReturnID=o.ReturnID, PurchaseID=o.PurchaseID,
        SupplierID=o.SupplierID, WarehouseID=o.WarehouseID,
        ReturnDate=o.ReturnDate, Status=o.Status,
        TotalAmount=float(o.TotalAmount or 0),
        Operator=o.Operator, ReturnOperator=o.ReturnOperator,
        RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
        Remark=o.Remark,
        SupplierName=supplier_name, WarehouseName=wh_name,
        Details=[PurchaseReturnDetailOut.model_validate(d) for d in details],
    )


@purchase_return_router.post("/", response_model=PurchaseReturnOrderOut)
def create_purchase_return(data: PurchaseReturnCreate, db: Session = Depends(get_db)):
    if db.query(PurchaseReturnOrder).filter(
        PurchaseReturnOrder.ReturnID == data.ReturnID).first():
        raise HTTPException(status_code=400, detail="退货单编号已存在")

    # 校验采购单存在
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.PurchaseID == data.PurchaseID).first()
    if not po:
        raise HTTPException(status_code=404, detail="原采购单不存在")

    total = sum(d.Amount for d in data.Details)
    order = PurchaseReturnOrder(
        ReturnID=data.ReturnID, PurchaseID=data.PurchaseID,
        SupplierID=data.SupplierID, WarehouseID=data.WarehouseID,
        ReturnDate=data.ReturnDate or datetime.now(),
        Status="草稿", TotalAmount=total,
        Operator=data.Operator, Remark=data.Remark,
    )
    db.add(order)
    db.flush()

    for item in data.Details:
        db.add(PurchaseReturnDetail(
            ReturnDetailID=item.ReturnDetailID, ReturnID=data.ReturnID,
            PurchaseDetailID=item.PurchaseDetailID,
            ProductID=item.ProductID, Quantity=item.Quantity,
            UnitPrice=item.UnitPrice, Amount=item.Amount,
        ))

    db.commit()
    db.refresh(order)
    return order


@purchase_return_router.put("/{return_id}", response_model=PurchaseReturnOrderOut)
def update_purchase_return(return_id: str, data: PurchaseReturnUpdate,
                            db: Session = Depends(get_db)):
    o = db.query(PurchaseReturnOrder).filter(
        PurchaseReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购退货单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的退货单才能修改")

    for key, val in data.model_dump(exclude_unset=True, exclude={'Details'}).items():
        setattr(o, key, val)

    if data.Details is not None:
        old_details = db.query(PurchaseReturnDetail).filter(
            PurchaseReturnDetail.ReturnID == return_id).all()
        for od in old_details:
            db.delete(od)
        db.flush()

        total = 0
        for item in data.Details:
            detail = PurchaseReturnDetail(
                ReturnDetailID=item.ReturnDetailID, ReturnID=return_id,
                PurchaseDetailID=item.PurchaseDetailID,
                ProductID=item.ProductID, Quantity=item.Quantity,
                UnitPrice=item.UnitPrice, Amount=item.Amount,
            )
            total += detail.Amount
            db.add(detail)

        o.TotalAmount = total

    db.commit()
    db.refresh(o)
    return o


@purchase_return_router.delete("/{return_id}")
def delete_purchase_return(return_id: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseReturnOrder).filter(
        PurchaseReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购退货单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的退货单才能删除")
    db.query(PurchaseReturnDetail).filter(
        PurchaseReturnDetail.ReturnID == return_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


@purchase_return_router.post("/{return_id}/execute")
def execute_purchase_return(return_id: str, operator: str = "系统",
                             db: Session = Depends(get_db)):
    """审核采购退货：扣减库存"""
    o = db.query(PurchaseReturnOrder).filter(
        PurchaseReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购退货单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的退货单才能审核")

    # 校验原采购单状态
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.PurchaseID == o.PurchaseID).first()
    if not po:
        raise HTTPException(status_code=404, detail="原采购单不存在")
    if po.Status != "已入库":
        raise HTTPException(status_code=400, detail="原采购单尚未入库，无法退货")

    details = db.query(PurchaseReturnDetail).filter(
        PurchaseReturnDetail.ReturnID == return_id).all()

    now = datetime.now()
    try:
        # 转换为dict列表供工具函数使用
        detail_dicts = [
            {
                "PurchaseDetailID": d.PurchaseDetailID,
                "ProductID": d.ProductID,
                "Quantity": float(d.Quantity),
                "UnitPrice": float(d.UnitPrice),
            }
            for d in details
        ]

        stock_apply_purchase_return(db, o.WarehouseID, detail_dicts, now)

        o.Status = "已退货"
        o.ReturnOperator = operator
        o.ReturnDate = now

        # 更新原采购单状态
        # 计算该采购单已累计退货数量
        total_returned = db.execute(text("""
            SELECT COALESCE(SUM(rd.Quantity), 0)
            FROM PurchaseReturnDetail rd
            JOIN PurchaseReturnOrder ro ON rd.ReturnID = ro.ReturnID
            WHERE ro.PurchaseID = :pid AND ro.Status = '已退货'
        """), {"pid": o.PurchaseID}).scalar()

        total_purchased = db.execute(text("""
            SELECT COALESCE(SUM(Quantity), 0)
            FROM PurchaseDetail
            WHERE PurchaseID = :pid
        """), {"pid": o.PurchaseID}).scalar()

        if total_returned >= total_purchased:
            po.Status = "已退货"
        else:
            po.Status = "部分退货"

        db.commit()
        return {"message": "退货审核成功", "status": "已退货"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"退货审核失败：{str(e)}")


@purchase_return_router.post("/{return_id}/rollback")
def rollback_purchase_return(return_id: str, operator: str = "系统",
                              db: Session = Depends(get_db)):
    """采购退货回退"""
    o = db.query(PurchaseReturnOrder).filter(
        PurchaseReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="采购退货单不存在")
    if o.Status != "已退货":
        raise HTTPException(status_code=400, detail="只有已退货状态的退货单才能回退")

    details = db.query(PurchaseReturnDetail).filter(
        PurchaseReturnDetail.ReturnID == return_id).all()

    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.PurchaseID == o.PurchaseID).first()

    now = datetime.now()
    try:
        detail_dicts = [
            {
                "PurchaseDetailID": d.PurchaseDetailID,
                "ProductID": d.ProductID,
                "Quantity": float(d.Quantity),
                "UnitPrice": float(d.UnitPrice),
            }
            for d in details
        ]

        stock_rollback_purchase_return(db, return_id, o.WarehouseID, detail_dicts, now)

        o.Status = "已回退"
        o.RollbackDate = now
        o.RollbackOperator = operator

        # 恢复原采购单状态
        if po:
            po.Status = "已入库"

        db.commit()
        return {"message": "退货回退成功", "status": "已回退"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"退货回退失败：{str(e)}")


# ====================================================================
#  销售退货
# ====================================================================
sale_return_router = APIRouter(prefix="/sale-returns", tags=["销售退货"])


@sale_return_router.get("/", response_model=List[SaleReturnOrderFullOut])
def list_sale_returns(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(SaleReturnOrder)
    if status:
        query = query.filter(SaleReturnOrder.Status == status)
    if customer_id:
        query = query.filter(SaleReturnOrder.CustomerID == customer_id)
    orders = query.order_by(SaleReturnOrder.ReturnDate.desc()).all()

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
        details = db.query(SaleReturnDetail).filter(
            SaleReturnDetail.ReturnID == o.ReturnID).all()
        result.append(SaleReturnOrderFullOut(
            ReturnID=o.ReturnID, SaleID=o.SaleID,
            CustomerID=o.CustomerID, WarehouseID=o.WarehouseID,
            ReturnDate=o.ReturnDate, Status=o.Status,
            TotalAmount=float(o.TotalAmount or 0),
            Operator=o.Operator, ReturnOperator=o.ReturnOperator,
            RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
            Remark=o.Remark,
            CustomerName=customer_map.get(o.CustomerID),
            WarehouseName=wh_map.get(o.WarehouseID),
            Details=[SaleReturnDetailOut.model_validate(d) for d in details],
        ))
    return result


@sale_return_router.get("/{return_id}", response_model=SaleReturnOrderFullOut)
def get_sale_return(return_id: str, db: Session = Depends(get_db)):
    o = db.query(SaleReturnOrder).filter(
        SaleReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售退货单不存在")
    details = db.query(SaleReturnDetail).filter(
        SaleReturnDetail.ReturnID == return_id).all()
    customer_name = db.execute(
        text("SELECT CustomerName FROM Customer WHERE CustomerID = :cid"),
        {"cid": o.CustomerID}).scalar()
    wh_name = db.execute(
        text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
        {"wid": o.WarehouseID}).scalar()
    return SaleReturnOrderFullOut(
        ReturnID=o.ReturnID, SaleID=o.SaleID,
        CustomerID=o.CustomerID, WarehouseID=o.WarehouseID,
        ReturnDate=o.ReturnDate, Status=o.Status,
        TotalAmount=float(o.TotalAmount or 0),
        Operator=o.Operator, ReturnOperator=o.ReturnOperator,
        RollbackDate=o.RollbackDate, RollbackOperator=o.RollbackOperator,
        Remark=o.Remark,
        CustomerName=customer_name, WarehouseName=wh_name,
        Details=[SaleReturnDetailOut.model_validate(d) for d in details],
    )


@sale_return_router.post("/", response_model=SaleReturnOrderOut)
def create_sale_return(data: SaleReturnCreate, db: Session = Depends(get_db)):
    if db.query(SaleReturnOrder).filter(
        SaleReturnOrder.ReturnID == data.ReturnID).first():
        raise HTTPException(status_code=400, detail="退货单编号已存在")

    so = db.query(SaleOrder).filter(
        SaleOrder.SaleID == data.SaleID).first()
    if not so:
        raise HTTPException(status_code=404, detail="原销售单不存在")

    total = sum(d.Amount for d in data.Details)
    order = SaleReturnOrder(
        ReturnID=data.ReturnID, SaleID=data.SaleID,
        CustomerID=data.CustomerID, WarehouseID=data.WarehouseID,
        ReturnDate=data.ReturnDate or datetime.now(),
        Status="草稿", TotalAmount=total,
        Operator=data.Operator, Remark=data.Remark,
    )
    db.add(order)
    db.flush()

    for item in data.Details:
        db.add(SaleReturnDetail(
            ReturnDetailID=item.ReturnDetailID, ReturnID=data.ReturnID,
            SaleDetailID=item.SaleDetailID,
            ProductID=item.ProductID, Quantity=item.Quantity,
            UnitPrice=item.UnitPrice, Amount=item.Amount,
        ))

    db.commit()
    db.refresh(order)
    return order


@sale_return_router.put("/{return_id}", response_model=SaleReturnOrderOut)
def update_sale_return(return_id: str, data: SaleReturnUpdate,
                        db: Session = Depends(get_db)):
    o = db.query(SaleReturnOrder).filter(
        SaleReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售退货单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的退货单才能修改")

    for key, val in data.model_dump(exclude_unset=True, exclude={'Details'}).items():
        setattr(o, key, val)

    if data.Details is not None:
        old_details = db.query(SaleReturnDetail).filter(
            SaleReturnDetail.ReturnID == return_id).all()
        for od in old_details:
            db.delete(od)
        db.flush()

        total = 0
        for item in data.Details:
            detail = SaleReturnDetail(
                ReturnDetailID=item.ReturnDetailID, ReturnID=return_id,
                SaleDetailID=item.SaleDetailID,
                ProductID=item.ProductID, Quantity=item.Quantity,
                UnitPrice=item.UnitPrice, Amount=item.Amount,
            )
            total += detail.Amount
            db.add(detail)

        o.TotalAmount = total

    db.commit()
    db.refresh(o)
    return o


@sale_return_router.delete("/{return_id}")
def delete_sale_return(return_id: str, db: Session = Depends(get_db)):
    o = db.query(SaleReturnOrder).filter(
        SaleReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售退货单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的退货单才能删除")
    db.query(SaleReturnDetail).filter(
        SaleReturnDetail.ReturnID == return_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


@sale_return_router.post("/{return_id}/execute")
def execute_sale_return(return_id: str, operator: str = "系统",
                         db: Session = Depends(get_db)):
    """审核销售退货：恢复库存"""
    o = db.query(SaleReturnOrder).filter(
        SaleReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售退货单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的退货单才能审核")

    so = db.query(SaleOrder).filter(
        SaleOrder.SaleID == o.SaleID).first()
    if not so:
        raise HTTPException(status_code=404, detail="原销售单不存在")
    if so.Status != "已出库":
        raise HTTPException(status_code=400, detail="原销售单尚未出库，无法退货")

    details = db.query(SaleReturnDetail).filter(
        SaleReturnDetail.ReturnID == return_id).all()

    now = datetime.now()
    try:
        detail_dicts = [
            {
                "SaleDetailID": d.SaleDetailID,
                "ProductID": d.ProductID,
                "Quantity": float(d.Quantity),
                "UnitPrice": float(d.UnitPrice),
            }
            for d in details
        ]

        stock_apply_sale_return(db, o.WarehouseID, detail_dicts, now)

        o.Status = "已退货"
        o.ReturnOperator = operator
        o.ReturnDate = now

        # 更新原销售单状态
        so.Status = "已退货"

        db.commit()
        return {"message": "销售退货审核成功", "status": "已退货"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"销售退货审核失败：{str(e)}")


@sale_return_router.post("/{return_id}/rollback")
def rollback_sale_return(return_id: str, operator: str = "系统",
                          db: Session = Depends(get_db)):
    """销售退货回退"""
    o = db.query(SaleReturnOrder).filter(
        SaleReturnOrder.ReturnID == return_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="销售退货单不存在")
    if o.Status != "已退货":
        raise HTTPException(status_code=400, detail="只有已退货状态的退货单才能回退")

    details = db.query(SaleReturnDetail).filter(
        SaleReturnDetail.ReturnID == return_id).all()

    so = db.query(SaleOrder).filter(
        SaleOrder.SaleID == o.SaleID).first()

    now = datetime.now()
    try:
        detail_dicts = [
            {
                "SaleDetailID": d.SaleDetailID,
                "ProductID": d.ProductID,
                "Quantity": float(d.Quantity),
                "UnitPrice": float(d.UnitPrice),
            }
            for d in details
        ]

        stock_rollback_sale_return(db, return_id, o.WarehouseID, detail_dicts, now)

        o.Status = "已回退"
        o.RollbackDate = now
        o.RollbackOperator = operator

        if so:
            so.Status = "已出库"

        db.commit()
        return {"message": "销售退货回退成功", "status": "已回退"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"销售退货回退失败：{str(e)}")


# 注册子路由到主router
router.include_router(purchase_return_router)
router.include_router(sale_return_router)
