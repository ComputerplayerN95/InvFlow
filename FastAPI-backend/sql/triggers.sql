-- ============================================
-- 触发器: 进销存实时库存更新
-- 设计思路: 在采购明细/销售明细/调拨明细的 INSERT/UPDATE/DELETE 上
-- 设置触发器，配合订单状态变更实现库存实时同步
-- ============================================

DELIMITER $$

-- ============================================
-- 1. 采购明细插入触发器 → 入库逻辑
--    当插入采购明细时，若对应采购单状态为"已入库"，自动更新库存
-- ============================================
CREATE TRIGGER IF NOT EXISTS trg_purchase_detail_insert
AFTER INSERT ON PurchaseDetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);
    DECLARE v_new_avg_price DECIMAL(18,2);
    DECLARE v_old_qty DECIMAL(18,2);
    DECLARE v_old_avg DECIMAL(18,2);
    DECLARE v_old_amount DECIMAL(18,2);
    DECLARE v_new_amount DECIMAL(18,2);
    DECLARE v_total_qty DECIMAL(18,2);

    -- 获取采购单状态和仓库
    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM PurchaseOrder WHERE PurchaseID = NEW.PurchaseID;

    -- 仅当状态为"已入库"时才更新库存
    IF v_status = '已入库' THEN
        -- 更新仓库库存
        INSERT INTO WarehouseStock (ProductID, WarehouseID, Quantity, LastUpdated)
        VALUES (NEW.ProductID, v_warehouse_id, NEW.Quantity, NOW())
        ON DUPLICATE KEY UPDATE
            Quantity = Quantity + NEW.Quantity,
            LastUpdated = NOW();

        -- 更新库存总表（进货均价法）
        SELECT IFNULL(TotalQuantity, 0), IFNULL(AveragePrice, 0)
        INTO v_old_qty, v_old_avg
        FROM TotalStock WHERE ProductID = NEW.ProductID;

        IF v_old_qty = 0 THEN
            SET v_new_avg_price = NEW.UnitPrice;
        ELSE
            SET v_old_amount = v_old_qty * v_old_avg;
            SET v_new_amount = NEW.Quantity * NEW.UnitPrice;
            SET v_total_qty = v_old_qty + NEW.Quantity;
            SET v_new_avg_price = (v_old_amount + v_new_amount) / v_total_qty;
        END IF;

        INSERT INTO TotalStock (ProductID, TotalQuantity, AveragePrice, LastPurchasePrice, LastUpdated)
        VALUES (NEW.ProductID, NEW.Quantity, v_new_avg_price, NEW.UnitPrice, NOW())
        ON DUPLICATE KEY UPDATE
            TotalQuantity = TotalQuantity + NEW.Quantity,
            AveragePrice = v_new_avg_price,
            LastPurchasePrice = NEW.UnitPrice,
            LastUpdated = NOW();

        -- 插入批次库存（FIFO）
        INSERT INTO BatchStock (BatchID, ProductID, WarehouseID, PurchaseDetailID, InDate, UnitPrice, RemainingQty)
        VALUES (CONCAT('BATCH', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'), FLOOR(RAND() * 10000)),
                NEW.ProductID, v_warehouse_id, NEW.PurchaseDetailID, NOW(), NEW.UnitPrice, NEW.Quantity);
    END IF;
END$$

-- ============================================
-- 2. 采购明细删除触发器 → 入库回退逻辑
-- ============================================
CREATE TRIGGER IF NOT EXISTS trg_purchase_detail_delete
AFTER DELETE ON PurchaseDetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);

    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM PurchaseOrder WHERE PurchaseID = OLD.PurchaseID;

    IF v_status = '已入库' THEN
        -- 回退仓库库存
        UPDATE WarehouseStock
        SET Quantity = Quantity - OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_warehouse_id;

        -- 回退库存总表
        UPDATE TotalStock
        SET TotalQuantity = TotalQuantity - OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID;
    END IF;
END$$

-- ============================================
-- 3. 销售明细插入触发器 → 出库逻辑
-- ============================================
CREATE TRIGGER IF NOT EXISTS trg_sale_detail_insert
AFTER INSERT ON SaleDetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);
    DECLARE v_remaining_qty DECIMAL(18,2);
    DECLARE v_need_qty DECIMAL(18,2);
    DECLARE v_batch_id VARCHAR(20);
    DECLARE v_unit_price DECIMAL(18,2);
    DECLARE v_deduct_qty DECIMAL(18,2);
    DECLARE v_done INT DEFAULT 0;
    DECLARE cur CURSOR FOR
        SELECT BatchID, UnitPrice, RemainingQty
        FROM BatchStock
        WHERE ProductID = NEW.ProductID AND WarehouseID = v_warehouse_id AND RemainingQty > 0
        ORDER BY InDate ASC;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM SaleOrder WHERE SaleID = NEW.SaleID;

    IF v_status = '已出库' THEN
        -- 更新仓库库存
        UPDATE WarehouseStock
        SET Quantity = Quantity - NEW.Quantity, LastUpdated = NOW()
        WHERE ProductID = NEW.ProductID AND WarehouseID = v_warehouse_id;

        -- 更新库存总表
        UPDATE TotalStock
        SET TotalQuantity = TotalQuantity - NEW.Quantity, LastUpdated = NOW()
        WHERE ProductID = NEW.ProductID;

        -- FIFO 出库：按批次顺序扣减
        SET v_need_qty = NEW.Quantity;
        OPEN cur;
        read_loop: LOOP
            FETCH cur INTO v_batch_id, v_unit_price, v_remaining_qty;
            IF v_done THEN LEAVE read_loop; END IF;

            IF v_remaining_qty >= v_need_qty THEN
                UPDATE BatchStock SET RemainingQty = RemainingQty - v_need_qty WHERE BatchID = v_batch_id;
                SET v_need_qty = 0;
                LEAVE read_loop;
            ELSE
                UPDATE BatchStock SET RemainingQty = 0 WHERE BatchID = v_batch_id;
                SET v_need_qty = v_need_qty - v_remaining_qty;
            END IF;
        END LOOP;
        CLOSE cur;
    END IF;
END$$

-- ============================================
-- 4. 销售明细删除触发器 → 出库回退逻辑
-- ============================================
CREATE TRIGGER IF NOT EXISTS trg_sale_detail_delete
AFTER DELETE ON SaleDetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_warehouse_id VARCHAR(20);

    SELECT Status, WarehouseID INTO v_status, v_warehouse_id
    FROM SaleOrder WHERE SaleID = OLD.SaleID;

    IF v_status = '已出库' THEN
        -- 回退仓库库存
        UPDATE WarehouseStock
        SET Quantity = Quantity + OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_warehouse_id;

        -- 回退库存总表
        UPDATE TotalStock
        SET TotalQuantity = TotalQuantity + OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID;
    END IF;
END$$

-- ============================================
-- 5. 调拨明细插入触发器 → 调拨审核通过后的出入库
-- ============================================
CREATE TRIGGER IF NOT EXISTS trg_transfer_detail_insert
AFTER INSERT ON TransferDetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_from_wh VARCHAR(20);
    DECLARE v_to_wh VARCHAR(20);

    SELECT Status, FromWarehouseID, ToWarehouseID
    INTO v_status, v_from_wh, v_to_wh
    FROM TransferOrder WHERE TransferID = NEW.TransferID;

    IF v_status = '已审核' THEN
        -- 调出仓库出库
        UPDATE WarehouseStock
        SET Quantity = Quantity - NEW.Quantity, LastUpdated = NOW()
        WHERE ProductID = NEW.ProductID AND WarehouseID = v_from_wh;

        -- 调入仓库入库
        INSERT INTO WarehouseStock (ProductID, WarehouseID, Quantity, LastUpdated)
        VALUES (NEW.ProductID, v_to_wh, NEW.Quantity, NOW())
        ON DUPLICATE KEY UPDATE
            Quantity = Quantity + NEW.Quantity,
            LastUpdated = NOW();

        -- 总库存不变（只是仓库间转移）
    END IF;
END$$

-- ============================================
-- 6. 调拨明细删除触发器 → 调拨审核回退
-- ============================================
CREATE TRIGGER IF NOT EXISTS trg_transfer_detail_delete
AFTER DELETE ON TransferDetail
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(10);
    DECLARE v_from_wh VARCHAR(20);
    DECLARE v_to_wh VARCHAR(20);

    SELECT Status, FromWarehouseID, ToWarehouseID
    INTO v_status, v_from_wh, v_to_wh
    FROM TransferOrder WHERE TransferID = OLD.TransferID;

    IF v_status = '已审核' THEN
        -- 调出仓库回退
        UPDATE WarehouseStock
        SET Quantity = Quantity + OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_from_wh;

        -- 调入仓库回退
        UPDATE WarehouseStock
        SET Quantity = Quantity - OLD.Quantity, LastUpdated = NOW()
        WHERE ProductID = OLD.ProductID AND WarehouseID = v_to_wh;
    END IF;
END$$

DELIMITER ;
