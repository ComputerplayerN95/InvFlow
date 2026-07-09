from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
import random
from ..database import get_db
from ..models import (
    StockCheckOrder, StockCheckDetail,
    ProfitLossOrder, ProfitLossDetail,
    WarehouseStock, TotalStock, BatchStock,
)
from ..schemas import (
    StockCheckCreate, StockCheckUpdate, StockCheckOrderOut,
    StockCheckDetailOut, StockCheckOrderFullOut, StockCheckDetailItem,
    ProfitLossCreate, ProfitLossUpdate, ProfitLossOrderOut,
    ProfitLossDetailOut, ProfitLossOrderFullOut, ProfitLossDetailItem,
    MessageResponse,
)
from ..utils.stock_utils import apply_profit_loss as stock_apply_profit_loss, rollback_profit_loss as stock_rollback_profit_loss

router = APIRouter(prefix="/api", tags=["盘点管理"])


# ====================================================================
#  盘点单
# ====================================================================
stock_check_router = APIRouter(prefix="/stock-checks", tags=["盘点单"])


@stock_check_router.get("/", response_model=List[StockCheckOrderFullOut])
def list_stock_checks(
    status: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(StockCheckOrder)
    if status:
        query = query.filter(StockCheckOrder.Status == status)
    if warehouse_id:
        query = query.filter(StockCheckOrder.WarehouseID == warehouse_id)
    orders = query.order_by(StockCheckOrder.CheckDate.desc()).all()

    wh_ids = list(set(o.WarehouseID for o in orders))
    wh_map = {}
    if wh_ids:
        rows = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseID IN :ids"),
                          {"ids": tuple(wh_ids)}).mappings().all()
        wh_map = {r["WarehouseID"]: r["WarehouseName"] for r in rows}

    result = []
    for o in orders:
        details = db.query(StockCheckDetail).filter(
            StockCheckDetail.CheckID == o.CheckID).all()
        result.append(StockCheckOrderFullOut(
            CheckID=o.CheckID, WarehouseID=o.WarehouseID,
            CheckDate=o.CheckDate, Status=o.Status,
            Operator=o.Operator, AuditOperator=o.AuditOperator,
            AuditDate=o.AuditDate, RollbackDate=o.RollbackDate,
            RollbackOperator=o.RollbackOperator, Remark=o.Remark,
            WarehouseName=wh_map.get(o.WarehouseID),
            Details=[StockCheckDetailOut.model_validate(d) for d in details],
        ))
    return result


@stock_check_router.get("/{check_id}", response_model=StockCheckOrderFullOut)
def get_stock_check(check_id: str, db: Session = Depends(get_db)):
    o = db.query(StockCheckOrder).filter(
        StockCheckOrder.CheckID == check_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    details = db.query(StockCheckDetail).filter(
        StockCheckDetail.CheckID == check_id).all()
    wh_name = db.execute(
        text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
        {"wid": o.WarehouseID}).scalar()
    return StockCheckOrderFullOut(
        CheckID=o.CheckID, WarehouseID=o.WarehouseID,
        CheckDate=o.CheckDate, Status=o.Status,
        Operator=o.Operator, AuditOperator=o.AuditOperator,
        AuditDate=o.AuditDate, RollbackDate=o.RollbackDate,
        RollbackOperator=o.RollbackOperator, Remark=o.Remark,
        WarehouseName=wh_name,
        Details=[StockCheckDetailOut.model_validate(d) for d in details],
    )


@stock_check_router.post("/", response_model=StockCheckOrderOut)
def create_stock_check(data: StockCheckCreate, db: Session = Depends(get_db)):
    """创建盘点草稿，自动填充账面库存"""
    if db.query(StockCheckOrder).filter(
        StockCheckOrder.CheckID == data.CheckID).first():
        raise HTTPException(status_code=400, detail="盘点单编号已存在")

    order = StockCheckOrder(
        CheckID=data.CheckID, WarehouseID=data.WarehouseID,
        CheckDate=data.CheckDate or datetime.now(),
        Status="草稿", Operator=data.Operator, Remark=data.Remark,
    )
    db.add(order)
    db.flush()

    if data.Details:
        for item in data.Details:
            db.add(StockCheckDetail(
                CheckDetailID=item.CheckDetailID, CheckID=data.CheckID,
                ProductID=item.ProductID,
                BookQuantity=item.BookQuantity,
                ActualQuantity=item.ActualQuantity,
                DiffQuantity=item.DiffQuantity,
                UnitPrice=item.UnitPrice,
                Remark=item.Remark,
            ))
    else:
        # 自动从 WarehouseStock 获取该仓库的商品账面库存
        ws_list = db.query(WarehouseStock).filter(
            WarehouseStock.WarehouseID == data.WarehouseID
        ).all()
        idx = 0
        for ws in ws_list:
            idx += 1
            ts = db.query(TotalStock).filter(
                TotalStock.ProductID == ws.ProductID).first()
            unit_price = float(ts.AveragePrice) if ts and ts.AveragePrice else 0
            db.add(StockCheckDetail(
                CheckDetailID=f"SCD{data.CheckID}{str(idx).zfill(2)}",
                CheckID=data.CheckID,
                ProductID=ws.ProductID,
                BookQuantity=float(ws.Quantity),
                ActualQuantity=float(ws.Quantity),  # 默认与账面一致
                DiffQuantity=0,
                UnitPrice=unit_price,
            ))

    db.commit()
    db.refresh(order)
    return order


@stock_check_router.put("/{check_id}", response_model=StockCheckOrderOut)
def update_stock_check(check_id: str, data: StockCheckUpdate,
                        db: Session = Depends(get_db)):
    o = db.query(StockCheckOrder).filter(
        StockCheckOrder.CheckID == check_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的盘点单才能修改")

    for key, val in data.model_dump(exclude_unset=True, exclude={'Details'}).items():
        setattr(o, key, val)

    if data.Details is not None:
        old_details = db.query(StockCheckDetail).filter(
            StockCheckDetail.CheckID == check_id).all()
        for od in old_details:
            db.delete(od)
        db.flush()

        for item in data.Details:
            diff = float(item.ActualQuantity) - float(item.BookQuantity)
            db.add(StockCheckDetail(
                CheckDetailID=item.CheckDetailID, CheckID=check_id,
                ProductID=item.ProductID,
                BookQuantity=item.BookQuantity,
                ActualQuantity=item.ActualQuantity,
                DiffQuantity=diff,
                UnitPrice=item.UnitPrice,
                Remark=item.Remark,
            ))

    db.commit()
    db.refresh(o)
    return o


@stock_check_router.delete("/{check_id}")
def delete_stock_check(check_id: str, db: Session = Depends(get_db)):
    o = db.query(StockCheckOrder).filter(
        StockCheckOrder.CheckID == check_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的盘点单才能删除")
    db.query(StockCheckDetail).filter(
        StockCheckDetail.CheckID == check_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


@stock_check_router.post("/{check_id}/audit")
def audit_stock_check(check_id: str, operator: str = "系统",
                       db: Session = Depends(get_db)):
    """审核盘点单：计算差异，自动生成损益单"""
    o = db.query(StockCheckOrder).filter(
        StockCheckOrder.CheckID == check_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的盘点单才能审核")

    details = db.query(StockCheckDetail).filter(
        StockCheckDetail.CheckID == check_id).all()

    # 计算差异
    has_diff = False
    for d in details:
        diff = float(d.ActualQuantity) - float(d.BookQuantity)
        d.DiffQuantity = diff
        if diff != 0:
            has_diff = True

    if not has_diff:
        # 无差异，直接完成盘点
        o.Status = "已审核"
        o.AuditOperator = operator
        o.AuditDate = datetime.now()
        db.commit()
        return {"message": "盘点审核完成（无差异）", "status": "已审核",
                "profit_loss_id": None}

    # 自动生成损益单
    now = datetime.now()
    pl_id = f"PL{now.strftime('%Y%m%d%H%M%S')}{random.randint(10,99)}"

    total_amount = 0
    pl_details = []
    for d in details:
        diff = float(d.DiffQuantity)
        if diff == 0:
            continue
        price = float(d.UnitPrice or 0)
        amount = abs(diff) * price
        total_amount += amount
        pl_details.append({
            "ProfitLossDetailID": f"PLD{pl_id}{len(pl_details)+1:02d}",
            "ProductID": d.ProductID,
            "Quantity": diff,
            "UnitPrice": price,
            "Amount": amount,
            "BatchID": None,
            "Remark": f"盘点差异（账面{d.BookQuantity}，实盘{d.ActualQuantity}）",
        })

    pl_type = "盘盈" if any(d["Quantity"] > 0 for d in pl_details) else "盘亏"
    if any(d["Quantity"] > 0 for d in pl_details) and any(d["Quantity"] < 0 for d in pl_details):
        pl_type = "盘盈/盘亏"

    pl_order = ProfitLossOrder(
        ProfitLossID=pl_id,
        WarehouseID=o.WarehouseID,
        OrderDate=now,
        Type=pl_type,
        Status="草稿",  # 生成草稿损益单，需单独审核
        TotalAmount=total_amount,
        Operator=operator,
        CheckID=check_id,
    )
    db.add(pl_order)

    for pd_item in pl_details:
        db.add(ProfitLossDetail(**pd_item, ProfitLossID=pl_id))

    o.Status = "已审核"
    o.AuditOperator = operator
    o.AuditDate = now

    db.commit()
    return {
        "message": "盘点审核完成，已生成损益单",
        "status": "已审核",
        "profit_loss_id": pl_id,
    }


@stock_check_router.post("/{check_id}/rollback")
def rollback_stock_check(check_id: str, operator: str = "系统",
                          db: Session = Depends(get_db)):
    """回退盘点单"""
    o = db.query(StockCheckOrder).filter(
        StockCheckOrder.CheckID == check_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    if o.Status != "已审核":
        raise HTTPException(status_code=400, detail="只有已审核状态的盘点单才能回退")

    # 检查是否已生成损益单且损益单已审核
    pl_orders = db.query(ProfitLossOrder).filter(
        ProfitLossOrder.CheckID == check_id,
        ProfitLossOrder.Status != "草稿"
    ).all()
    if pl_orders:
        raise HTTPException(status_code=400,
                            detail="盘点单已生成已审核的损益单，请先回退损益单")

    now = datetime.now()
    o.Status = "已回退"
    o.RollbackDate = now
    o.RollbackOperator = operator
    db.commit()
    return {"message": "盘点单回退成功", "status": "已回退"}


# ====================================================================
#  损益单
# ====================================================================
profit_loss_router = APIRouter(prefix="/profit-loss", tags=["损益单"])


@profit_loss_router.get("/", response_model=List[ProfitLossOrderFullOut])
def list_profit_loss(
    status: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ProfitLossOrder)
    if status:
        query = query.filter(ProfitLossOrder.Status == status)
    if warehouse_id:
        query = query.filter(ProfitLossOrder.WarehouseID == warehouse_id)
    orders = query.order_by(ProfitLossOrder.OrderDate.desc()).all()

    wh_ids = list(set(o.WarehouseID for o in orders))
    wh_map = {}
    if wh_ids:
        rows = db.execute(text("SELECT WarehouseID, WarehouseName FROM Warehouse WHERE WarehouseID IN :ids"),
                          {"ids": tuple(wh_ids)}).mappings().all()
        wh_map = {r["WarehouseID"]: r["WarehouseName"] for r in rows}

    result = []
    for o in orders:
        details = db.query(ProfitLossDetail).filter(
            ProfitLossDetail.ProfitLossID == o.ProfitLossID).all()
        result.append(ProfitLossOrderFullOut(
            ProfitLossID=o.ProfitLossID, WarehouseID=o.WarehouseID,
            OrderDate=o.OrderDate, Type=o.Type, Status=o.Status,
            TotalAmount=float(o.TotalAmount or 0),
            Operator=o.Operator, AuditOperator=o.AuditOperator,
            AuditDate=o.AuditDate, RollbackDate=o.RollbackDate,
            RollbackOperator=o.RollbackOperator, Remark=o.Remark,
            CheckID=o.CheckID,
            WarehouseName=wh_map.get(o.WarehouseID),
            Details=[ProfitLossDetailOut.model_validate(d) for d in details],
        ))
    return result


@profit_loss_router.get("/{pl_id}", response_model=ProfitLossOrderFullOut)
def get_profit_loss(pl_id: str, db: Session = Depends(get_db)):
    o = db.query(ProfitLossOrder).filter(
        ProfitLossOrder.ProfitLossID == pl_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="损益单不存在")
    details = db.query(ProfitLossDetail).filter(
        ProfitLossDetail.ProfitLossID == pl_id).all()
    wh_name = db.execute(
        text("SELECT WarehouseName FROM Warehouse WHERE WarehouseID = :wid"),
        {"wid": o.WarehouseID}).scalar()
    return ProfitLossOrderFullOut(
        ProfitLossID=o.ProfitLossID, WarehouseID=o.WarehouseID,
        OrderDate=o.OrderDate, Type=o.Type, Status=o.Status,
        TotalAmount=float(o.TotalAmount or 0),
        Operator=o.Operator, AuditOperator=o.AuditOperator,
        AuditDate=o.AuditDate, RollbackDate=o.RollbackDate,
        RollbackOperator=o.RollbackOperator, Remark=o.Remark,
        CheckID=o.CheckID,
        WarehouseName=wh_name,
        Details=[ProfitLossDetailOut.model_validate(d) for d in details],
    )


@profit_loss_router.post("/", response_model=ProfitLossOrderOut)
def create_profit_loss(data: ProfitLossCreate, db: Session = Depends(get_db)):
    if db.query(ProfitLossOrder).filter(
        ProfitLossOrder.ProfitLossID == data.ProfitLossID).first():
        raise HTTPException(status_code=400, detail="损益单编号已存在")

    total = sum(d.Amount for d in data.Details)
    order = ProfitLossOrder(
        ProfitLossID=data.ProfitLossID, WarehouseID=data.WarehouseID,
        OrderDate=data.OrderDate or datetime.now(),
        Type=data.Type, Status="草稿", TotalAmount=total,
        Operator=data.Operator, Remark=data.Remark,
        CheckID=data.CheckID,
    )
    db.add(order)
    db.flush()

    for item in data.Details:
        db.add(ProfitLossDetail(
            ProfitLossDetailID=item.ProfitLossDetailID,
            ProfitLossID=data.ProfitLossID,
            ProductID=item.ProductID, Quantity=item.Quantity,
            UnitPrice=item.UnitPrice, Amount=item.Amount,
            BatchID=item.BatchID, Remark=item.Remark,
        ))

    db.commit()
    db.refresh(order)
    return order


@profit_loss_router.put("/{pl_id}", response_model=ProfitLossOrderOut)
def update_profit_loss(pl_id: str, data: ProfitLossUpdate,
                        db: Session = Depends(get_db)):
    o = db.query(ProfitLossOrder).filter(
        ProfitLossOrder.ProfitLossID == pl_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="损益单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的损益单才能修改")

    for key, val in data.model_dump(exclude_unset=True, exclude={'Details'}).items():
        setattr(o, key, val)

    if data.Details is not None:
        old_details = db.query(ProfitLossDetail).filter(
            ProfitLossDetail.ProfitLossID == pl_id).all()
        for od in old_details:
            db.delete(od)
        db.flush()

        total = 0
        for item in data.Details:
            detail = ProfitLossDetail(
                ProfitLossDetailID=item.ProfitLossDetailID,
                ProfitLossID=pl_id,
                ProductID=item.ProductID, Quantity=item.Quantity,
                UnitPrice=item.UnitPrice, Amount=item.Amount,
                BatchID=item.BatchID, Remark=item.Remark,
            )
            total += detail.Amount
            db.add(detail)

        o.TotalAmount = total

    db.commit()
    db.refresh(o)
    return o


@profit_loss_router.delete("/{pl_id}")
def delete_profit_loss(pl_id: str, db: Session = Depends(get_db)):
    o = db.query(ProfitLossOrder).filter(
        ProfitLossOrder.ProfitLossID == pl_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="损益单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的损益单才能删除")
    db.query(ProfitLossDetail).filter(
        ProfitLossDetail.ProfitLossID == pl_id).delete()
    db.delete(o)
    db.commit()
    return {"message": "删除成功"}


@profit_loss_router.post("/{pl_id}/audit")
def audit_profit_loss(pl_id: str, operator: str = "系统",
                       db: Session = Depends(get_db)):
    """审核损益单：调整库存"""
    o = db.query(ProfitLossOrder).filter(
        ProfitLossOrder.ProfitLossID == pl_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="损益单不存在")
    if o.Status != "草稿":
        raise HTTPException(status_code=400, detail="只有草稿状态的损益单才能审核")

    details = db.query(ProfitLossDetail).filter(
        ProfitLossDetail.ProfitLossID == pl_id).all()

    now = datetime.now()
    try:
        pl_dicts = [
            {
                "ProductID": d.ProductID,
                "Quantity": float(d.Quantity),
                "UnitPrice": float(d.UnitPrice),
                "ProfitLossDetailID": d.ProfitLossDetailID,
            }
            for d in details
        ]

        stock_apply_profit_loss(db, o.WarehouseID, pl_dicts, now)

        o.Status = "已审核"
        o.AuditOperator = operator
        o.AuditDate = now

        db.commit()
        return {"message": "损益审核成功，库存已调整", "status": "已审核"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"损益审核失败：{str(e)}")


@profit_loss_router.post("/{pl_id}/rollback")
def rollback_profit_loss(pl_id: str, operator: str = "系统",
                          db: Session = Depends(get_db)):
    """损益回退"""
    o = db.query(ProfitLossOrder).filter(
        ProfitLossOrder.ProfitLossID == pl_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="损益单不存在")
    if o.Status != "已审核":
        raise HTTPException(status_code=400, detail="只有已审核状态的损益单才能回退")

    details = db.query(ProfitLossDetail).filter(
        ProfitLossDetail.ProfitLossID == pl_id).all()

    now = datetime.now()
    try:
        pl_dicts = [
            {
                "ProductID": d.ProductID,
                "Quantity": float(d.Quantity),
                "UnitPrice": float(d.UnitPrice),
                "ProfitLossDetailID": d.ProfitLossDetailID,
            }
            for d in details
        ]

        stock_rollback_profit_loss(db, pl_id, o.WarehouseID, pl_dicts, now)

        o.Status = "已回退"
        o.RollbackDate = now
        o.RollbackOperator = operator

        db.commit()
        return {"message": "损益回退成功", "status": "已回退"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"损益回退失败：{str(e)}")


# 注册子路由到主router
router.include_router(stock_check_router)
router.include_router(profit_loss_router)
