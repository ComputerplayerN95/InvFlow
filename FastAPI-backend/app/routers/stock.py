from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from ..database import get_db
from ..models import TotalStock, WarehouseStock, MonthlyStock, Product, Category
from ..schemas import (
    TotalStockOut, WarehouseStockOut, MonthlyStockOut,
    MonthlySettlementRequest, AntiSettlementRequest, MessageResponse
)

router = APIRouter(prefix="/api/stock", tags=["库存与结转"])


# ==================== 总库存查询 ====================
@router.get("/total", response_model=List[TotalStockOut])
def list_total_stock(
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """库存总表：支持按类别筛选"""
    sql = """
        SELECT ts.ProductID, p.ProductName, ts.TotalQuantity,
               ts.AveragePrice, ts.LastPurchasePrice, ts.LastUpdated
        FROM TotalStock ts
        JOIN Product p ON ts.ProductID = p.ProductID
        WHERE (:cid IS NULL OR p.CategoryID = :cid)
        ORDER BY p.ProductID
    """
    rows = db.execute(text(sql), {"cid": category_id}).mappings().all()
    return [dict(r) for r in rows]


# ==================== 仓库库存查询 ====================
@router.get("/warehouse", response_model=List[WarehouseStockOut])
def list_warehouse_stock(
    warehouse_id: Optional[str] = None,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """各仓库库存查询"""
    sql = """
        SELECT ws.ProductID, ws.WarehouseID, ws.Quantity, ws.LastUpdated,
               p.ProductName, w.WarehouseName
        FROM WarehouseStock ws
        JOIN Product p ON ws.ProductID = p.ProductID
        JOIN Warehouse w ON ws.WarehouseID = w.WarehouseID
        WHERE (:wid IS NULL OR ws.WarehouseID = :wid)
          AND (:pid IS NULL OR ws.ProductID = :pid)
        ORDER BY ws.WarehouseID, ws.ProductID
    """
    rows = db.execute(text(sql), {"wid": warehouse_id, "pid": product_id}).mappings().all()
    return [dict(r) for r in rows]


# ==================== 月度结存 ====================
@router.get("/monthly", response_model=List[MonthlyStockOut])
def list_monthly_stock(
    year_month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """月度结存查询"""
    sql = """
        SELECT ms.*, p.ProductName, c.CategoryName
        FROM MonthlyStock ms
        JOIN Product p ON ms.ProductID = p.ProductID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        WHERE (:ym IS NULL OR ms.YearMonth = :ym)
        ORDER BY ms.YearMonth DESC, ms.ProductID
    """
    rows = db.execute(text(sql), {"ym": year_month}).mappings().all()
    return [dict(r) for r in rows]


@router.post("/monthly/settle", response_model=MessageResponse)
def do_monthly_settlement(req: MonthlySettlementRequest, db: Session = Depends(get_db)):
    """执行月度结存"""
    try:
        db.execute(
            text("CALL sp_monthly_settlement(:ym, :op)"),
            {"ym": req.YearMonth, "op": req.Operator}
        )
        db.commit()
        return {"message": f"{req.YearMonth} 月度结存完成", "success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/monthly/anti-settle", response_model=MessageResponse)
def do_anti_monthly_settlement(req: AntiSettlementRequest, db: Session = Depends(get_db)):
    """执行反月结"""
    try:
        db.execute(
            text("CALL sp_anti_monthly_settlement(:ym)"),
            {"ym": req.YearMonth}
        )
        db.commit()
        return {"message": f"{req.YearMonth} 反结存完成", "success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 按月类别库存统计 ====================
@router.get("/summary/by-category")
def stock_summary_by_category(db: Session = Depends(get_db)):
    """按类别统计库存"""
    try:
        db.execute(text("CALL sp_stock_by_category()"))
        rows = db.execute(text("CALL sp_stock_by_category()")).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        rows = db.execute(text("""
            SELECT c.CategoryID, c.CategoryName,
                   COUNT(DISTINCT p.ProductID) AS product_count,
                   COALESCE(SUM(ts.TotalQuantity), 0) AS total_quantity,
                   COALESCE(SUM(ts.TotalQuantity * ts.AveragePrice), 0) AS total_amount
            FROM Category c
            LEFT JOIN Product p ON c.CategoryID = p.CategoryID
            LEFT JOIN TotalStock ts ON p.ProductID = ts.ProductID
            GROUP BY c.CategoryID, c.CategoryName
        """)).mappings().all()
        return [dict(r) for r in rows]
