-- ============================================
-- 7.1.2 运维需求变更：FIFO先进先出法成本核算
-- 策略：不改变原有均价法代码，在数据库端做加法
-- ============================================

-- 1. SaleOutBatch 表：记录每笔销售明细从哪个 FIFO 批次扣的
DROP TABLE IF EXISTS SaleOutBatch;
CREATE TABLE SaleOutBatch (
    SaleOutBatchID VARCHAR(30) PRIMARY KEY COMMENT '销售出库批次编号',
    SaleDetailID   VARCHAR(20) NOT NULL COMMENT '销售明细编号',
    BatchID        VARCHAR(20) NOT NULL COMMENT '来源批次编号(FK→BatchStock)',
    Quantity       DECIMAL(18,2) NOT NULL COMMENT '从该批次扣减的数量',
    UnitPrice      DECIMAL(18,2) NOT NULL COMMENT '该批次的入库单价(即FIFO成本)',
    OutDate        DATETIME NOT NULL COMMENT '出库时间',
    INDEX idx_sale_detail (SaleDetailID),
    INDEX idx_batch (BatchID),
    FOREIGN KEY (SaleDetailID) REFERENCES SaleDetail(SaleDetailID) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (BatchID) REFERENCES BatchStock(BatchID) 
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='FIFO出库批次明细——记录每笔销售从哪个批次扣的，用于FIFO成本核算';


-- 2. 存储过程：使用 FIFO 实际成本计算月度销售毛利
DROP PROCEDURE IF EXISTS sp_monthly_sales_profit_fifo;
DELIMITER $$
CREATE PROCEDURE sp_monthly_sales_profit_fifo(
    IN p_year_month VARCHAR(7)
)
BEGIN
    SELECT 
        p.ProductID,
        p.ProductName,
        p.Spec,
        p.Unit,
        c.CategoryID,
        c.CategoryName,
        SUM(sd.Quantity) AS total_sale_qty,
        SUM(sd.Amount) AS total_sale_amount,
        ROUND(SUM(sob.Quantity * sob.UnitPrice) / NULLIF(SUM(sd.Quantity), 0), 2) AS avg_fifo_cost_price,
        SUM(sob.Quantity * sob.UnitPrice) AS total_fifo_cost_amount,
        SUM(sd.Amount) - SUM(sob.Quantity * sob.UnitPrice) AS fifo_gross_profit,
        CASE 
            WHEN SUM(sd.Amount) > 0 
            THEN ROUND((SUM(sd.Amount) - SUM(sob.Quantity * sob.UnitPrice)) / SUM(sd.Amount) * 100, 2)
            ELSE 0 
        END AS fifo_profit_rate
    FROM SaleDetail sd
    JOIN SaleOrder so ON sd.SaleID = so.SaleID
    JOIN Product p ON sd.ProductID = p.ProductID
    LEFT JOIN Category c ON p.CategoryID = c.CategoryID
    LEFT JOIN SaleOutBatch sob ON sd.SaleDetailID = sob.SaleDetailID
    WHERE so.Status = '已出库'
      AND DATE_FORMAT(so.OutDate, '%Y-%m') = p_year_month
    GROUP BY p.ProductID, p.ProductName, p.Spec, p.Unit, c.CategoryID, c.CategoryName
    ORDER BY fifo_gross_profit DESC;
END$$
DELIMITER ;


-- 3. 存储过程：FIFO vs 均价法对比报表
DROP PROCEDURE IF EXISTS sp_monthly_cost_comparison;
DELIMITER $$
CREATE PROCEDURE sp_monthly_cost_comparison(
    IN p_year_month VARCHAR(7)
)
BEGIN
    SELECT 
        p.ProductID,
        p.ProductName,
        c.CategoryName,
        -- 均价法成本（从TotalStock.AveragePrice）
        IFNULL(ts.AveragePrice, 0) AS avg_price_method_cost,
        SUM(sd.Quantity) * IFNULL(ts.AveragePrice, 0) AS avg_price_total_cost,
        -- FIFO实际成本（从SaleOutBatch）
        COALESCE(fifo.fifo_unit_cost, 0) AS fifo_method_cost,
        COALESCE(fifo.fifo_total_cost, 0) AS fifo_total_cost,
        -- 差异
        COALESCE(fifo.fifo_total_cost, 0) - SUM(sd.Quantity) * IFNULL(ts.AveragePrice, 0) AS cost_diff,
        -- 毛利差异
        (SUM(sd.Amount) - COALESCE(fifo.fifo_total_cost, 0)) 
          - (SUM(sd.Amount) - SUM(sd.Quantity) * IFNULL(ts.AveragePrice, 0)) AS profit_diff
    FROM SaleDetail sd
    JOIN SaleOrder so ON sd.SaleID = so.SaleID
    JOIN Product p ON sd.ProductID = p.ProductID
    LEFT JOIN Category c ON p.CategoryID = c.CategoryID
    LEFT JOIN TotalStock ts ON sd.ProductID = ts.ProductID
    LEFT JOIN (
        SELECT sd2.ProductID,
               ROUND(SUM(sob2.Quantity * sob2.UnitPrice) / NULLIF(SUM(sd2.Quantity), 0), 2) AS fifo_unit_cost,
               SUM(sob2.Quantity * sob2.UnitPrice) AS fifo_total_cost
        FROM SaleDetail sd2
        JOIN SaleOrder so2 ON sd2.SaleID = so2.SaleID
        JOIN SaleOutBatch sob2 ON sd2.SaleDetailID = sob2.SaleDetailID
        WHERE so2.Status = '已出库'
          AND DATE_FORMAT(so2.OutDate, '%Y-%m') = p_year_month
        GROUP BY sd2.ProductID
    ) fifo ON sd.ProductID = fifo.ProductID
    WHERE so.Status = '已出库'
      AND DATE_FORMAT(so.OutDate, '%Y-%m') = p_year_month
    GROUP BY p.ProductID, p.ProductName, c.CategoryName, ts.AveragePrice, fifo.fifo_unit_cost, fifo.fifo_total_cost
    ORDER BY profit_diff DESC;
END$$
DELIMITER ;
