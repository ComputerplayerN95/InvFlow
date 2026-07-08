from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/api/reports", tags=["报表"])


# ==================== 出入库月度明细账 ====================
@router.get("/monthly-detail")
def monthly_detail_report(
    year_month: str = Query(..., description="年月，格式YYYY-MM"),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """出入库月度明细账：上月结存、本月入库明细、本月出库明细、本月结存"""
    # Note: MySQL stored procedures return multiple result sets,
    # which pymysql can handle but SQLAlchemy doesn't easily support.
    # Using direct SQL queries instead for compatibility.

    # 上月结存
    begin_rows = db.execute(text("""
        SELECT ms.ProductID, p.ProductName, p.Spec, p.Unit, c.CategoryName,
               ms.BeginQty AS last_month_end_qty, ms.BeginAmount AS last_month_end_amount
        FROM MonthlyStock ms
        JOIN Product p ON ms.ProductID = p.ProductID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        WHERE ms.YearMonth = :ym
          AND (:pid IS NULL OR ms.ProductID = :pid)
    """), {"ym": year_month, "pid": product_id}).mappings().all()

    # 本月入库明细
    in_rows = db.execute(text("""
        SELECT pd.ProductID, p.ProductName, p.Spec, p.Unit,
               po.PurchaseID, po.InDate AS operate_date,
               pd.Quantity AS in_qty, pd.UnitPrice AS in_price, pd.Amount AS in_amount,
               po.SupplierID, s.SupplierName
        FROM PurchaseDetail pd
        JOIN PurchaseOrder po ON pd.PurchaseID = po.PurchaseID
        JOIN Product p ON pd.ProductID = p.ProductID
        LEFT JOIN Supplier s ON po.SupplierID = s.SupplierID
        WHERE po.Status = '已入库'
          AND DATE_FORMAT(po.InDate, '%Y-%m') = :ym
          AND (:pid IS NULL OR pd.ProductID = :pid)
        ORDER BY po.InDate
    """), {"ym": year_month, "pid": product_id}).mappings().all()

    # 本月出库明细
    out_rows = db.execute(text("""
        SELECT sd.ProductID, p.ProductName, p.Spec, p.Unit,
               so.SaleID, so.OutDate AS operate_date,
               sd.Quantity AS out_qty, sd.UnitPrice AS out_price, sd.Amount AS out_amount,
               so.CustomerID, cu.CustomerName
        FROM SaleDetail sd
        JOIN SaleOrder so ON sd.SaleID = so.SaleID
        JOIN Product p ON sd.ProductID = p.ProductID
        LEFT JOIN Customer cu ON so.CustomerID = cu.CustomerID
        WHERE so.Status = '已出库'
          AND DATE_FORMAT(so.OutDate, '%Y-%m') = :ym
          AND (:pid IS NULL OR sd.ProductID = :pid)
        ORDER BY so.OutDate
    """), {"ym": year_month, "pid": product_id}).mappings().all()

    # 本月结存
    end_rows = db.execute(text("""
        SELECT ms.ProductID, p.ProductName, p.Spec, p.Unit,
               ms.EndQty AS month_end_qty, ms.EndAmount AS month_end_amount
        FROM MonthlyStock ms
        JOIN Product p ON ms.ProductID = p.ProductID
        WHERE ms.YearMonth = :ym
          AND (:pid IS NULL OR ms.ProductID = :pid)
    """), {"ym": year_month, "pid": product_id}).mappings().all()

    return {
        "year_month": year_month,
        "begin_stock": [dict(r) for r in begin_rows],
        "in_details": [dict(r) for r in in_rows],
        "out_details": [dict(r) for r in out_rows],
        "end_stock": [dict(r) for r in end_rows],
    }


# ==================== 月度销售毛利统计报表 ====================
@router.get("/monthly-sales-profit")
def monthly_sales_profit(
    year_month: str = Query(..., description="年月，格式YYYY-MM"),
    db: Session = Depends(get_db),
):
    """月度销售毛利统计报表（存储过程实现）"""
    rows = db.execute(text("""
        SELECT sd.ProductID, p.ProductName, p.Spec, p.Unit,
               c.CategoryID, c.CategoryName,
               SUM(sd.Quantity) AS total_sale_qty,
               SUM(sd.Amount) AS total_sale_amount,
               COALESCE(ts.AveragePrice, 0) AS avg_cost_price,
               SUM(sd.Quantity) * COALESCE(ts.AveragePrice, 0) AS total_cost_amount,
               SUM(sd.Amount) - SUM(sd.Quantity) * COALESCE(ts.AveragePrice, 0) AS gross_profit,
               CASE WHEN SUM(sd.Amount) > 0
                    THEN ROUND((SUM(sd.Amount) - SUM(sd.Quantity) * COALESCE(ts.AveragePrice, 0)) / SUM(sd.Amount) * 100, 2)
                    ELSE 0 END AS profit_rate
        FROM SaleDetail sd
        JOIN SaleOrder so ON sd.SaleID = so.SaleID
        JOIN Product p ON sd.ProductID = p.ProductID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        LEFT JOIN TotalStock ts ON sd.ProductID = ts.ProductID
        WHERE so.Status = '已出库'
          AND DATE_FORMAT(so.OutDate, '%Y-%m') = :ym
        GROUP BY sd.ProductID, p.ProductName, p.Spec, p.Unit, c.CategoryID, c.CategoryName, ts.AveragePrice
        ORDER BY gross_profit DESC
    """), {"ym": year_month}).mappings().all()

    return {
        "year_month": year_month,
        "report": [dict(r) for r in rows],
    }


# ==================== 采购单综合查询报表 ====================
@router.get("/purchase-query")
def purchase_query_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """按时间、供应商、类别、商品查询采购单明细"""
    rows = db.execute(text("""
        SELECT po.PurchaseID, po.OrderDate, po.Status, po.TotalAmount,
               po.InDate, po.Operator, po.InOperator,
               s.SupplierID, s.SupplierName,
               w.WarehouseID, w.WarehouseName,
               pd.PurchaseDetailID, pd.ProductID, p.ProductName, p.Spec,
               c.CategoryName, pd.Quantity, pd.UnitPrice, pd.Amount
        FROM PurchaseOrder po
        JOIN PurchaseDetail pd ON po.PurchaseID = pd.PurchaseID
        JOIN Product p ON pd.ProductID = p.ProductID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        LEFT JOIN Supplier s ON po.SupplierID = s.SupplierID
        LEFT JOIN Warehouse w ON po.WarehouseID = w.WarehouseID
        WHERE (:sd IS NULL OR po.OrderDate >= :sd)
          AND (:ed IS NULL OR po.OrderDate <= CONCAT(:ed, ' 23:59:59'))
          AND (:sid IS NULL OR po.SupplierID = :sid)
          AND (:cid IS NULL OR c.CategoryID = :cid)
          AND (:pid IS NULL OR pd.ProductID = :pid)
        ORDER BY po.OrderDate DESC, po.PurchaseID
    """), {"sd": start_date, "ed": end_date, "sid": supplier_id,
           "cid": category_id, "pid": product_id}).mappings().all()

    return [dict(r) for r in rows]


# ==================== 销售单综合查询报表 ====================
@router.get("/sale-query")
def sale_query_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """按时间、客户、类别、商品查询销售单明细"""
    rows = db.execute(text("""
        SELECT so.SaleID, so.OrderDate, so.Status, so.TotalAmount,
               so.OutDate, so.Operator, so.OutOperator,
               cu.CustomerID, cu.CustomerName,
               w.WarehouseID, w.WarehouseName,
               sd.SaleDetailID, sd.ProductID, p.ProductName, p.Spec,
               c.CategoryName, sd.Quantity, sd.UnitPrice, sd.Amount
        FROM SaleOrder so
        JOIN SaleDetail sd ON so.SaleID = sd.SaleID
        JOIN Product p ON sd.ProductID = p.ProductID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        LEFT JOIN Customer cu ON so.CustomerID = cu.CustomerID
        LEFT JOIN Warehouse w ON so.WarehouseID = w.WarehouseID
        WHERE (:sd IS NULL OR so.OrderDate >= :sd)
          AND (:ed IS NULL OR so.OrderDate <= CONCAT(:ed, ' 23:59:59'))
          AND (:cusid IS NULL OR so.CustomerID = :cusid)
          AND (:cid IS NULL OR c.CategoryID = :cid)
          AND (:pid IS NULL OR sd.ProductID = :pid)
        ORDER BY so.OrderDate DESC, so.SaleID
    """), {"sd": start_date, "ed": end_date, "cusid": customer_id,
           "cid": category_id, "pid": product_id}).mappings().all()

    return [dict(r) for r in rows]


# ==================== Agent扩展预留接口 ====================
@router.get("/agent/sales-profit")
def agent_sales_profit(
    year_month: str = Query(..., description="年月，格式YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Agent扩展接口 - 销售毛利统计（预留AI Agent调用）"""
    return monthly_sales_profit(year_month, db)


@router.get("/agent/stock-summary")
def agent_stock_summary(db: Session = Depends(get_db)):
    """Agent扩展接口 - 库存汇总"""
    rows = db.execute(text("""
        SELECT p.ProductID, p.ProductName, c.CategoryName,
               ts.TotalQuantity, ts.AveragePrice,
               ts.TotalQuantity * ts.AveragePrice AS total_value
        FROM TotalStock ts
        JOIN Product p ON ts.ProductID = p.ProductID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        ORDER BY total_value DESC
    """)).mappings().all()
    return {"summary": [dict(r) for r in rows]}
