-- ============================================
-- 视图: vw_ProductInfo (商品信息视图)
-- 用途: 查询商品时直接展示商品类型名称
-- ============================================
CREATE OR REPLACE VIEW vw_ProductInfo AS
SELECT
    p.ProductID,
    p.ProductName,
    p.Spec,
    p.Unit,
    p.Remark,
    p.CategoryID,
    c.CategoryName,
    -- 可选：带上总库存和均价（方便商品列表页展示）
    ts.TotalQuantity,
    ts.AveragePrice,
    ts.LastPurchasePrice
FROM
    Product p
LEFT JOIN
    Category c ON p.CategoryID = c.CategoryID
LEFT JOIN
    TotalStock ts ON p.ProductID = ts.ProductID;