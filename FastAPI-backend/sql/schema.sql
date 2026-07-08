-- ============================================
-- 数据库: 进销存管理系统 (MySQL)
-- 字符集: utf8mb4
-- 修正说明：修复主键逻辑、增加唯一约束、新增FIFO批次表
-- ============================================

-- 1. 商品类型表 (父表)
CREATE TABLE IF NOT EXISTS Category (
    CategoryID     VARCHAR(20)   PRIMARY KEY COMMENT '类型编号',
    CategoryName   VARCHAR(50)   NOT NULL COMMENT '类型名称',
    Description    VARCHAR(200)           COMMENT '类型描述'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品类型';

-- 2. 仓库表 (父表)
CREATE TABLE IF NOT EXISTS Warehouse (
    WarehouseID    VARCHAR(20)   PRIMARY KEY COMMENT '仓库编号',
    WarehouseName  VARCHAR(50)   NOT NULL COMMENT '仓库名称',
    Location       VARCHAR(100)          COMMENT '仓库地址',
    Phone          VARCHAR(20)           COMMENT '联系电话'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库';

-- 3. 供应商表 (父表)
CREATE TABLE IF NOT EXISTS Supplier (
    SupplierID     VARCHAR(20)   PRIMARY KEY COMMENT '供应商编号',
    SupplierName   VARCHAR(50)   NOT NULL COMMENT '供应商名称',
    Contact        VARCHAR(20)           COMMENT '联系人',
    Phone          VARCHAR(20)           COMMENT '联系电话',
    Address        VARCHAR(100)          COMMENT '联系地址'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商';

-- 4. 客户表 (父表)
CREATE TABLE IF NOT EXISTS Customer (
    CustomerID     VARCHAR(20)   PRIMARY KEY COMMENT '客户编号',
    CustomerName   VARCHAR(50)   NOT NULL COMMENT '客户名称',
    Contact        VARCHAR(20)           COMMENT '联系人',
    Phone          VARCHAR(20)           COMMENT '联系电话',
    Address        VARCHAR(100)          COMMENT '联系地址'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户';

-- 5. 商品表 (子表, 依赖 Category)
CREATE TABLE IF NOT EXISTS Product (
    ProductID      VARCHAR(20)   PRIMARY KEY COMMENT '商品编号',
    CategoryID     VARCHAR(20)   NOT NULL COMMENT '类型编号',
    ProductName    VARCHAR(50)   NOT NULL COMMENT '商品名称',
    Spec           VARCHAR(50)           COMMENT '规格型号',
    Unit           VARCHAR(10)           COMMENT '计量单位',
    Remark         VARCHAR(200)          COMMENT '备注',
    FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品';

-- 6. 商品供应商关联表
CREATE TABLE IF NOT EXISTS ProductSupplier (
    ProductSupplierID VARCHAR(20) PRIMARY KEY COMMENT '商品供应商编号',
    ProductID         VARCHAR(20) NOT NULL COMMENT '商品编号',
    SupplierID        VARCHAR(20) NOT NULL COMMENT '供应商编号',
    SupplyPrice       DECIMAL(18,2) COMMENT '供应价格',
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID) ON DELETE RESTRICT ON UPDATE CASCADE,
    -- 【修正】增加唯一约束：同一个供应商不能重复供应同一个商品
    UNIQUE KEY uk_product_supplier (ProductID, SupplierID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品供应商';

-- 7. 仓库库存表
CREATE TABLE IF NOT EXISTS WarehouseStock (
    ProductID        VARCHAR(20) NOT NULL COMMENT '商品编号',
    WarehouseID      VARCHAR(20) NOT NULL COMMENT '仓库编号',
    Quantity         DECIMAL(18,2) DEFAULT 0 COMMENT '库存数量',
    LastUpdated      DATETIME COMMENT '最后更新时间',
    -- 【修正】直接使用联合主键，确保一个仓库一种商品只有一条记录
    PRIMARY KEY (ProductID, WarehouseID),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库库存';

-- 8. 库存总表
CREATE TABLE IF NOT EXISTS TotalStock (
    ProductID          VARCHAR(20) NOT NULL PRIMARY KEY COMMENT '商品编号',
    TotalQuantity      DECIMAL(18,2) DEFAULT 0 COMMENT '总库存数量',
    AveragePrice       DECIMAL(18,2) DEFAULT 0 COMMENT '进货均价',
    LastPurchasePrice  DECIMAL(18,2) DEFAULT 0 COMMENT '最后一次采购价',
    LastUpdated        DATETIME COMMENT '最后更新时间',
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存总表';

-- 9. 月度结存表
CREATE TABLE IF NOT EXISTS MonthlyStock (
    MonthlyStockID VARCHAR(20) PRIMARY KEY COMMENT '月度结存编号',
    ProductID      VARCHAR(20) NOT NULL COMMENT '商品编号',
    YearMonth      VARCHAR(7)  NOT NULL COMMENT '年月 (格式: YYYY-MM)',
    BeginQty       DECIMAL(18,2) DEFAULT 0 COMMENT '期初数量',
    BeginAmount    DECIMAL(18,2) DEFAULT 0 COMMENT '期初金额',
    InQty          DECIMAL(18,2) DEFAULT 0 COMMENT '本期入库数量',
    InAmount       DECIMAL(18,2) DEFAULT 0 COMMENT '本期入库金额',
    OutQty         DECIMAL(18,2) DEFAULT 0 COMMENT '本期出库数量',
    OutAmount      DECIMAL(18,2) DEFAULT 0 COMMENT '本期出库金额',
    EndQty         DECIMAL(18,2) DEFAULT 0 COMMENT '期末数量',
    EndAmount      DECIMAL(18,2) DEFAULT 0 COMMENT '期末金额',
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE,
    UNIQUE KEY uk_product_month (ProductID, YearMonth)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月度结存';

-- 10. 采购单
CREATE TABLE IF NOT EXISTS PurchaseOrder (
    PurchaseID     VARCHAR(20)   PRIMARY KEY COMMENT '采购单编号',
    SupplierID     VARCHAR(20)   NOT NULL COMMENT '供应商编号',
    WarehouseID    VARCHAR(20)   NOT NULL COMMENT '入库仓库编号',
    OrderDate      DATETIME               COMMENT '采购日期',
    Status         VARCHAR(10)   DEFAULT '草稿' COMMENT '单据状态 (草稿/已入库/已回退)',
    TotalAmount    DECIMAL(18,2) DEFAULT 0 COMMENT '总金额',
    Operator       VARCHAR(20)            COMMENT '操作人',
    InDate         DATETIME               COMMENT '入库时间',
    InOperator     VARCHAR(20)            COMMENT '入库操作人',
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购单';

-- 11. 采购单明细
CREATE TABLE IF NOT EXISTS PurchaseDetail (
    PurchaseDetailID VARCHAR(20) PRIMARY KEY COMMENT '采购单明细编号',
    PurchaseID       VARCHAR(20) NOT NULL COMMENT '采购单编号',
    ProductID        VARCHAR(20) NOT NULL COMMENT '商品编号',
    Quantity         DECIMAL(18,2) DEFAULT 0 COMMENT '采购数量',
    UnitPrice        DECIMAL(18,2) DEFAULT 0 COMMENT '采购单价',
    Amount           DECIMAL(18,2) DEFAULT 0 COMMENT '金额小计',
    FOREIGN KEY (PurchaseID) REFERENCES PurchaseOrder(PurchaseID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购单明细';

-- 12. 销售单
CREATE TABLE IF NOT EXISTS SaleOrder (
    SaleID         VARCHAR(20)   PRIMARY KEY COMMENT '销售单编号',
    CustomerID     VARCHAR(20)   NOT NULL COMMENT '客户编号',
    WarehouseID    VARCHAR(20)   NOT NULL COMMENT '出库仓库编号',
    OrderDate      DATETIME               COMMENT '销售日期',
    Status         VARCHAR(10)   DEFAULT '草稿' COMMENT '单据状态 (草稿/已出库/已回退)',
    TotalAmount    DECIMAL(18,2) DEFAULT 0 COMMENT '总金额',
    Operator       VARCHAR(20)            COMMENT '操作人',
    OutDate        DATETIME               COMMENT '出库时间',
    OutOperator    VARCHAR(20)            COMMENT '出库操作人',
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售单';

-- 13. 销售单明细
CREATE TABLE IF NOT EXISTS SaleDetail (
    SaleDetailID   VARCHAR(20) PRIMARY KEY COMMENT '销售单明细编号',
    SaleID         VARCHAR(20) NOT NULL COMMENT '销售单编号',
    ProductID      VARCHAR(20) NOT NULL COMMENT '商品编号',
    Quantity       DECIMAL(18,2) DEFAULT 0 COMMENT '销售数量',
    UnitPrice      DECIMAL(18,2) DEFAULT 0 COMMENT '销售单价',
    Amount         DECIMAL(18,2) DEFAULT 0 COMMENT '金额小计',
    FOREIGN KEY (SaleID) REFERENCES SaleOrder(SaleID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售单明细';

-- 14. 调拨单
CREATE TABLE IF NOT EXISTS TransferOrder (
    TransferID       VARCHAR(20) PRIMARY KEY COMMENT '调拨单编号',
    FromWarehouseID  VARCHAR(20) NOT NULL COMMENT '调出仓库编号',
    ToWarehouseID    VARCHAR(20) NOT NULL COMMENT '调入仓库编号',
    OrderDate        DATETIME             COMMENT '调拨日期',
    Status           VARCHAR(10) DEFAULT '草稿' COMMENT '单据状态 (草稿/已审核/已回退)',
    Operator         VARCHAR(20)          COMMENT '操作人',
    FOREIGN KEY (FromWarehouseID) REFERENCES Warehouse(WarehouseID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (ToWarehouseID) REFERENCES Warehouse(WarehouseID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='调拨单';

-- 15. 调拨单明细
CREATE TABLE IF NOT EXISTS TransferDetail (
    TransferDetailID VARCHAR(20) PRIMARY KEY COMMENT '调拨单明细编号',
    TransferID       VARCHAR(20) NOT NULL COMMENT '调拨单编号',
    ProductID        VARCHAR(20) NOT NULL COMMENT '商品编号',
    Quantity         DECIMAL(18,2) DEFAULT 0 COMMENT '调拨数量',
    FOREIGN KEY (TransferID) REFERENCES TransferOrder(TransferID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='调拨单明细';

-- ============================================
-- 16. 先进先出批次余量表 (这是你代码里漏掉的致命缺失)
-- 用途：专门用于先进先出(FIFO)成本核算
-- ============================================
CREATE TABLE IF NOT EXISTS BatchStock (
    BatchID          VARCHAR(20) PRIMARY KEY COMMENT '批次流水号 (建议生成规则: BATCH+年月日+随机数)',
    ProductID        VARCHAR(20) NOT NULL COMMENT '商品编号',
    WarehouseID      VARCHAR(20) NOT NULL COMMENT '所在仓库',
    PurchaseDetailID VARCHAR(20) COMMENT '关联采购明细ID (溯源用，可为空)',
    InDate           DATETIME NOT NULL COMMENT '入库时间 (排序依据，先进先出靠这个时间)',
    UnitPrice        DECIMAL(18,2) NOT NULL COMMENT '该批次的采购单价',
    RemainingQty     DECIMAL(18,2) NOT NULL COMMENT '该批次剩余可出库数量',
    -- 联合索引：出库时按 (商品+仓库+时间) 排序查询，必须有这个索引！
    INDEX idx_batch_query (ProductID, WarehouseID, InDate),
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='先进先出批次余量表';

-- ============================================
-- 17. 回退字段补充
-- ============================================
ALTER TABLE PurchaseOrder 
ADD COLUMN RollbackDate DATETIME COMMENT '回退时间',
ADD COLUMN RollbackOperator VARCHAR(20) COMMENT '回退操作人';

ALTER TABLE SaleOrder 
ADD COLUMN RollbackDate DATETIME COMMENT '回退时间',
ADD COLUMN RollbackOperator VARCHAR(20) COMMENT '回退操作人';

ALTER TABLE BatchStock 
ADD COLUMN Quantity DECIMAL(18,2) DEFAULT 0 COMMENT '入库总数量';