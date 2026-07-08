-- ============================================
-- 存储过程: 进销存报表与月度结转
-- 先删后建，确保可重复执行
-- ============================================

DROP PROCEDURE IF EXISTS sp_monthly_settlement;
DROP PROCEDURE IF EXISTS sp_anti_monthly_settlement;
DROP PROCEDURE IF EXISTS sp_monthly_detail_report;
DROP PROCEDURE IF EXISTS sp_monthly_sales_profit;
DROP PROCEDURE IF EXISTS sp_stock_by_category;
DROP PROCEDURE IF EXISTS sp_monthly_purchase_report;
DROP PROCEDURE IF EXISTS sp_monthly_sale_report;
DROP PROCEDURE IF EXISTS sp_purchase_query_report;
DROP PROCEDURE IF EXISTS sp_sale_query_report;

DELIMITER $$

-- ============================================
-- 1. 月度结转存储过程
--    参数: p_year_month (格式: YYYY-MM)
-- ============================================
CREATE PROCEDURE sp_monthly_settlement(
    IN p_year_month VARCHAR(7),
    IN p_operator VARCHAR(20)
)
BEGIN
    DECLARE v_done INT DEFAULT 0;
    DECLARE v_product_id VARCHAR(20);
    DECLARE v_begin_qty DECIMAL(18,2);
    DECLARE v_begin_amount DECIMAL(18,2);
    DECLARE v_in_qty DECIMAL(18,2);
    DECLARE v_in_amount DECIMAL(18,2);
    DECLARE v_out_qty DECIMAL(18,2);
    DECLARE v_out_amount DECIMAL(18,2);
    DECLARE v_end_qty DECIMAL(18,2);
    DECLARE v_end_amount DECIMAL(18,2);
    DECLARE v_avg_price DECIMAL(18,2);

    DECLARE cur CURSOR FOR SELECT ProductID FROM Product;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    IF EXISTS (SELECT 1 FROM MonthlyStock WHERE YearMonth = p_year_month LIMIT 1) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该月份已结存，请先执行反结存';
    END IF;

    START TRANSACTION;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_product_id;
        IF v_done THEN LEAVE read_loop; END IF;

        SELECT EndQty, EndAmount INTO v_begin_qty, v_begin_amount
        FROM MonthlyStock
        WHERE ProductID = v_product_id
          AND YearMonth = DATE_FORMAT(DATE_SUB(CONCAT(p_year_month, '-01'), INTERVAL 1 MONTH), '%Y-%m')
        LIMIT 1;

        IF v_begin_qty IS NULL THEN
            SELECT IFNULL(TotalQuantity, 0), IFNULL(AveragePrice, 0)
            INTO v_begin_qty, v_avg_price
            FROM TotalStock WHERE ProductID = v_product_id;
            SET v_begin_amount = v_begin_qty * v_avg_price;
        END IF;

        SELECT IFNULL(SUM(pd.Quantity), 0), IFNULL(SUM(pd.Amount), 0)
        INTO v_in_qty, v_in_amount
        FROM PurchaseDetail pd
        JOIN PurchaseOrder po ON pd.PurchaseID = po.PurchaseID
        WHERE pd.ProductID = v_product_id
          AND po.Status = '已入库'
          AND DATE_FORMAT(po.InDate, '%Y-%m') = p_year_month;

        SELECT IFNULL(SUM(sd.Quantity), 0), IFNULL(SUM(sd.Amount), 0)
        INTO v_out_qty, v_out_amount
        FROM SaleDetail sd
        JOIN SaleOrder so ON sd.SaleID = so.SaleID
        WHERE sd.ProductID = v_product_id
          AND so.Status = '已出库'
          AND DATE_FORMAT(so.OutDate, '%Y-%m') = p_year_month;

        SET v_end_qty = v_begin_qty + v_in_qty - v_out_qty;
        SET v_end_amount = v_begin_amount + v_in_amount - v_out_amount;

        INSERT INTO MonthlyStock (MonthlyStockID, ProductID, YearMonth, BeginQty, BeginAmount, InQty, InAmount, OutQty, OutAmount, EndQty, EndAmount)
        VALUES (CONCAT('MS', REPLACE(p_year_month, '-', ''), v_product_id),
                v_product_id, p_year_month,
                v_begin_qty, v_begin_amount,
                v_in_qty, v_in_amount,
                v_out_qty, v_out_amount,
                v_end_qty, v_end_amount);

    END LOOP;
    CLOSE cur;

    COMMIT;
END$$

-- ============================================
-- 2. 反月结存储过程
-- ============================================
CREATE PROCEDURE sp_anti_monthly_settlement(
    IN p_year_month VARCHAR(7)
)
BEGIN
    DECLARE v_count INT;

    SELECT COUNT(*) INTO v_count FROM MonthlyStock WHERE YearMonth = p_year_month;

    IF v_count = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该月份未结存，无需反结存';
    END IF;

    DELETE FROM MonthlyStock WHERE YearMonth = p_year_month;
END$$

-- ============================================
-- 3. 出入库月度明细账
-- ============================================
CREATE PROCEDURE sp_monthly_detail_report(
    IN p_year_month VARCHAR(7),
    IN p_product_id VARCHAR(20)
)
BEGIN
    SELECT
        ms.ProductID,
        p.ProductName,
        p.Spec,
        p.Unit,
        c.CategoryName,
        ms.BeginQty AS last_month_end_qty,
        ms.BeginAmount AS last_month_end_amount
    FROM MonthlyStock ms
    JOIN Product p ON ms.ProductID = p.ProductID
    LEFT JOIN Category c ON p.CategoryID = c.CategoryID
    WHERE ms.YearMonth = p_year_month
      AND (p_product_id IS NULL OR ms.ProductID = p_product_id);

    SELECT
        pd.ProductID,
        p.ProductName,
        p.Spec,
        p.Unit,
        po.PurchaseID,
        po.InDate AS operate_date,
        pd.Quantity AS in_qty,
        pd.UnitPrice AS in_price,
        pd.Amount AS in_amount,
        po.SupplierID,
        s.SupplierName
    FROM PurchaseDetail pd
    JOIN PurchaseOrder po ON pd.PurchaseID = po.PurchaseID
    JOIN Product p ON pd.ProductID = p.ProductID
    LEFT JOIN Supplier s ON po.SupplierID = s.SupplierID
    WHERE po.Status = '已入库'
      AND DATE_FORMAT(po.InDate, '%Y-%m') = p_year_month
      AND (p_product_id IS NULL OR pd.ProductID = p_product_id)
    ORDER BY po.InDate;

    SELECT
        sd.ProductID,
        p.ProductName,
        p.Spec,
        p.Unit,
        so.SaleID,
        so.OutDate AS operate_date,
        sd.Quantity AS out_qty,
        sd.UnitPrice AS out_price,
        sd.Amount AS out_amount,
        so.CustomerID,
        cu.CustomerName
    FROM SaleDetail sd
    JOIN SaleOrder so ON sd.SaleID = so.SaleID
    JOIN Product p ON sd.ProductID = p.ProductID
    LEFT JOIN Customer cu ON so.CustomerID = cu.CustomerID
    WHERE so.Status = '已出库'
      AND DATE_FORMAT(so.OutDate, '%Y-%m') = p_year_month
      AND (p_product_id IS NULL OR sd.ProductID = p_product_id)
    ORDER BY so.OutDate;

    SELECT
        ms.ProductID,
        p.ProductName,
        p.Spec,
        p.Unit,
        ms.EndQty AS month_end_qty,
        ms.EndAmount AS month_end_amount
    FROM MonthlyStock ms
    JOIN Product p ON ms.ProductID = p.ProductID
    WHERE ms.YearMonth = p_year_month
      AND (p_product_id IS NULL OR ms.ProductID = p_product_id);
END$$

-- ============================================
-- 4. 月度销售毛利统计报表
-- ============================================
CREATE PROCEDURE sp_monthly_sales_profit(
    IN p_year_month VARCHAR(7)
)
BEGIN
    SELECT
        sd.ProductID,
        p.ProductName,
        p.Spec,
        p.Unit,
        c.CategoryID,
        c.CategoryName,
        SUM(sd.Quantity) AS total_sale_qty,
        SUM(sd.Amount) AS total_sale_amount,
        IFNULL(ts.AveragePrice, 0) AS avg_cost_price,
        SUM(sd.Quantity) * IFNULL(ts.AveragePrice, 0) AS total_cost_amount,
        SUM(sd.Amount) - SUM(sd.Quantity) * IFNULL(ts.AveragePrice, 0) AS gross_profit,
        CASE
            WHEN SUM(sd.Amount) > 0
            THEN ROUND((SUM(sd.Amount) - SUM(sd.Quantity) * IFNULL(ts.AveragePrice, 0)) / SUM(sd.Amount) * 100, 2)
            ELSE 0
        END AS profit_rate
    FROM SaleDetail sd
    JOIN SaleOrder so ON sd.SaleID = so.SaleID
    JOIN Product p ON sd.ProductID = p.ProductID
    LEFT JOIN Category c ON p.CategoryID = c.CategoryID
    LEFT JOIN TotalStock ts ON sd.ProductID = ts.ProductID
    WHERE so.Status = '已出库'
      AND DATE_FORMAT(so.OutDate, '%Y-%m') = p_year_month
    GROUP BY sd.ProductID, p.ProductName, p.Spec, p.Unit, c.CategoryID, c.CategoryName, ts.AveragePrice
    ORDER BY gross_profit DESC;
END$$

-- ============================================
-- 5. 按类别统计库存报表
-- ============================================
CREATE PROCEDURE sp_stock_by_category()
BEGIN
    SELECT
        c.CategoryID,
        c.CategoryName,
        COUNT(DISTINCT p.ProductID) AS product_count,
        SUM(IFNULL(ts.TotalQuantity, 0)) AS total_quantity,
        SUM(IFNULL(ts.TotalQuantity, 0) * IFNULL(ts.AveragePrice, 0)) AS total_amount
    FROM Category c
    LEFT JOIN Product p ON c.CategoryID = p.CategoryID
    LEFT JOIN TotalStock ts ON p.ProductID = ts.ProductID
    GROUP BY c.CategoryID, c.CategoryName;
END$$

-- ============================================
-- 6. 按月度统计采购报表
-- ============================================
CREATE PROCEDURE sp_monthly_purchase_report(
    IN p_year_month VARCHAR(7)
)
BEGIN
    SELECT
        DATE_FORMAT(po.InDate, '%Y-%m') AS ym,
        pd.ProductID,
        p.ProductName,
        s.SupplierID,
        s.SupplierName,
        SUM(pd.Quantity) AS total_qty,
        SUM(pd.Amount) AS total_amount
    FROM PurchaseDetail pd
    JOIN PurchaseOrder po ON pd.PurchaseID = po.PurchaseID
    JOIN Product p ON pd.ProductID = p.ProductID
    LEFT JOIN Supplier s ON po.SupplierID = s.SupplierID
    WHERE po.Status = '已入库'
      AND (p_year_month IS NULL OR DATE_FORMAT(po.InDate, '%Y-%m') = p_year_month)
    GROUP BY ym, pd.ProductID, p.ProductName, s.SupplierID, s.SupplierName
    ORDER BY ym, pd.ProductID;
END$$

-- ============================================
-- 7. 按月度统计销售报表
-- ============================================
CREATE PROCEDURE sp_monthly_sale_report(
    IN p_year_month VARCHAR(7)
)
BEGIN
    SELECT
        DATE_FORMAT(so.OutDate, '%Y-%m') AS ym,
        sd.ProductID,
        p.ProductName,
        cu.CustomerID,
        cu.CustomerName,
        SUM(sd.Quantity) AS total_qty,
        SUM(sd.Amount) AS total_amount
    FROM SaleDetail sd
    JOIN SaleOrder so ON sd.SaleID = so.SaleID
    JOIN Product p ON sd.ProductID = p.ProductID
    LEFT JOIN Customer cu ON so.CustomerID = cu.CustomerID
    WHERE so.Status = '已出库'
      AND (p_year_month IS NULL OR DATE_FORMAT(so.OutDate, '%Y-%m') = p_year_month)
    GROUP BY ym, sd.ProductID, p.ProductName, cu.CustomerID, cu.CustomerName
    ORDER BY ym, sd.ProductID;
END$$

-- ============================================
-- 8. 采购单按条件查询报表
-- ============================================
CREATE PROCEDURE sp_purchase_query_report(
    IN p_start_date VARCHAR(10),
    IN p_end_date VARCHAR(10),
    IN p_supplier_id VARCHAR(20),
    IN p_category_id VARCHAR(20),
    IN p_product_id VARCHAR(20)
)
BEGIN
    SELECT
        po.PurchaseID,
        po.OrderDate,
        po.Status,
        po.TotalAmount,
        po.InDate,
        po.Operator,
        po.InOperator,
        s.SupplierID,
        s.SupplierName,
        w.WarehouseID,
        w.WarehouseName,
        pd.PurchaseDetailID,
        pd.ProductID,
        p.ProductName,
        p.Spec,
        c.CategoryName,
        pd.Quantity,
        pd.UnitPrice,
        pd.Amount
    FROM PurchaseOrder po
    JOIN PurchaseDetail pd ON po.PurchaseID = pd.PurchaseID
    JOIN Product p ON pd.ProductID = p.ProductID
    LEFT JOIN Category c ON p.CategoryID = c.CategoryID
    LEFT JOIN Supplier s ON po.SupplierID = s.SupplierID
    LEFT JOIN Warehouse w ON po.WarehouseID = w.WarehouseID
    WHERE (p_start_date IS NULL OR po.OrderDate >= p_start_date)
      AND (p_end_date IS NULL OR po.OrderDate <= CONCAT(p_end_date, ' 23:59:59'))
      AND (p_supplier_id IS NULL OR po.SupplierID = p_supplier_id)
      AND (p_category_id IS NULL OR c.CategoryID = p_category_id)
      AND (p_product_id IS NULL OR pd.ProductID = p_product_id)
    ORDER BY po.OrderDate DESC, po.PurchaseID;
END$$

-- ============================================
-- 9. 销售单按条件查询报表
-- ============================================
CREATE PROCEDURE sp_sale_query_report(
    IN p_start_date VARCHAR(10),
    IN p_end_date VARCHAR(10),
    IN p_customer_id VARCHAR(20),
    IN p_category_id VARCHAR(20),
    IN p_product_id VARCHAR(20)
)
BEGIN
    SELECT
        so.SaleID,
        so.OrderDate,
        so.Status,
        so.TotalAmount,
        so.OutDate,
        so.Operator,
        so.OutOperator,
        cu.CustomerID,
        cu.CustomerName,
        w.WarehouseID,
        w.WarehouseName,
        sd.SaleDetailID,
        sd.ProductID,
        p.ProductName,
        p.Spec,
        c.CategoryName,
        sd.Quantity,
        sd.UnitPrice,
        sd.Amount
    FROM SaleOrder so
    JOIN SaleDetail sd ON so.SaleID = sd.SaleID
    JOIN Product p ON sd.ProductID = p.ProductID
    LEFT JOIN Category c ON p.CategoryID = c.CategoryID
    LEFT JOIN Customer cu ON so.CustomerID = cu.CustomerID
    LEFT JOIN Warehouse w ON so.WarehouseID = w.WarehouseID
    WHERE (p_start_date IS NULL OR so.OrderDate >= p_start_date)
      AND (p_end_date IS NULL OR so.OrderDate <= CONCAT(p_end_date, ' 23:59:59'))
      AND (p_customer_id IS NULL OR so.CustomerID = p_customer_id)
      AND (p_category_id IS NULL OR c.CategoryID = p_category_id)
      AND (p_product_id IS NULL OR sd.ProductID = p_product_id)
    ORDER BY so.OrderDate DESC, so.SaleID;
END$$

DELIMITER ;
