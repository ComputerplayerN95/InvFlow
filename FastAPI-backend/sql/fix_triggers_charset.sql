-- ===================================================
-- 修复触发器乱码问题
-- 根因：触发器创建时 MySQL 客户端使用 gbk 编码，
-- 导致中文文本('已入库'/'已出库'/'已审核')变成乱码
-- 乱码触发器与 utf8mb4 列比较时引发 1267 collation 错误
-- ===================================================
-- 使用方法：mysql -u root -p invflow-db < fix_triggers_charset.sql
-- ===================================================

-- 删除所有旧触发器（gbk 编码）
DROP TRIGGER IF EXISTS trg_purchase_detail_insert;
DROP TRIGGER IF EXISTS trg_purchase_detail_delete;
DROP TRIGGER IF EXISTS trg_sale_detail_insert;
DROP TRIGGER IF EXISTS trg_sale_detail_delete;
DROP TRIGGER IF EXISTS trg_transfer_detail_insert;
DROP TRIGGER IF EXISTS trg_transfer_detail_delete;

-- 重建触发器（确保客户端使用 utf8mb4 连接）
DELIMITER //

CREATE TRIGGER trg_purchase_detail_insert
AFTER INSERT ON purchasedetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);
    
    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM PurchaseOrder WHERE PurchaseID = NEW.PurchaseID;
    
    IF v_status = '已入库' THEN
        UPDATE WarehouseStock
        SET Quantity = Quantity + NEW.Quantity, LastUpdated = NOW()
        WHERE ProductID = NEW.ProductID AND WarehouseID = v_warehouse_id;
    END IF;
END //

CREATE TRIGGER trg_purchase_detail_delete
AFTER DELETE ON purchasedetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);
    
    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM PurchaseOrder WHERE PurchaseID = OLD.PurchaseID;
    
    IF v_status = '已入库' THEN
        UPDATE WarehouseStock
        SET Quantity = Quantity - OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_warehouse_id;
    END IF;
END //

CREATE TRIGGER trg_sale_detail_insert
AFTER INSERT ON saledetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);
    
    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM SaleOrder WHERE SaleID = NEW.SaleID;
    
    IF v_status = '已出库' THEN
        UPDATE WarehouseStock
        SET Quantity = Quantity - NEW.Quantity, LastUpdated = NOW()
        WHERE ProductID = NEW.ProductID AND WarehouseID = v_warehouse_id;
    END IF;
END //

CREATE TRIGGER trg_sale_detail_delete
AFTER DELETE ON saledetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);
    
    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM SaleOrder WHERE SaleID = OLD.SaleID;
    
    IF v_status = '已出库' THEN
        UPDATE WarehouseStock
        SET Quantity = Quantity + OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_warehouse_id;
    END IF;
END //

CREATE TRIGGER trg_transfer_detail_insert
AFTER INSERT ON transferdetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_from_wh VARCHAR(20);
    DECLARE v_to_wh VARCHAR(20);
    
    SELECT Status, FromWarehouseID, ToWarehouseID
    INTO v_status, v_from_wh, v_to_wh
    FROM TransferOrder WHERE TransferID = NEW.TransferID;
    
    IF v_status = '已审核' THEN
        UPDATE WarehouseStock
        SET Quantity = Quantity - NEW.Quantity, LastUpdated = NOW()
        WHERE ProductID = NEW.ProductID AND WarehouseID = v_from_wh;
        
        INSERT INTO WarehouseStock (ProductID, WarehouseID, Quantity, LastUpdated)
        VALUES (NEW.ProductID, v_to_wh, NEW.Quantity, NOW())
        ON DUPLICATE KEY UPDATE
            Quantity = Quantity + NEW.Quantity,
            LastUpdated = NOW();
    END IF;
END //

CREATE TRIGGER trg_transfer_detail_delete
AFTER DELETE ON transferdetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_from_wh VARCHAR(20);
    DECLARE v_to_wh VARCHAR(20);
    
    SELECT Status, FromWarehouseID, ToWarehouseID
    INTO v_status, v_from_wh, v_to_wh
    FROM TransferOrder WHERE TransferID = OLD.TransferID;
    
    IF v_status = '已审核' THEN
        UPDATE WarehouseStock
        SET Quantity = Quantity + OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_from_wh;
        
        UPDATE WarehouseStock
        SET Quantity = Quantity - OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_to_wh;
    END IF;
END //

DELIMITER ;
