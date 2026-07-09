-- ============================================================
-- InvFlow v2 升级脚本：FIFO成本法 + 退货&盘点功能
-- 创建8张新表
-- ============================================================

-- 采购退货主表
DROP TABLE IF EXISTS PurchaseReturnOrder;
CREATE TABLE PurchaseReturnOrder (
    ReturnID        VARCHAR(20)     NOT NULL PRIMARY KEY,
    PurchaseID      VARCHAR(20)     NOT NULL,
    SupplierID      VARCHAR(20)     NOT NULL,
    WarehouseID     VARCHAR(20)     NOT NULL,
    ReturnDate      DATETIME,
    Status          VARCHAR(10)     DEFAULT '草稿',
    TotalAmount     DECIMAL(18,2)   DEFAULT 0,
    Operator        VARCHAR(20),
    ReturnOperator  VARCHAR(20),
    RollbackDate    DATETIME,
    RollbackOperator VARCHAR(20),
    Remark          TEXT,
    FOREIGN KEY (PurchaseID)  REFERENCES PurchaseOrder(PurchaseID)  ON UPDATE CASCADE,
    FOREIGN KEY (SupplierID)  REFERENCES Supplier(SupplierID)       ON UPDATE CASCADE,
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID)     ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 采购退货明细
DROP TABLE IF EXISTS PurchaseReturnDetail;
CREATE TABLE PurchaseReturnDetail (
    ReturnDetailID    VARCHAR(20)   NOT NULL PRIMARY KEY,
    ReturnID          VARCHAR(20)   NOT NULL,
    PurchaseDetailID  VARCHAR(20)   NOT NULL,
    ProductID         VARCHAR(20)   NOT NULL,
    Quantity          DECIMAL(18,2) DEFAULT 0,
    UnitPrice         DECIMAL(18,2) DEFAULT 0,
    Amount            DECIMAL(18,2) DEFAULT 0,
    FOREIGN KEY (ReturnID)         REFERENCES PurchaseReturnOrder(ReturnID)   ON UPDATE CASCADE,
    FOREIGN KEY (PurchaseDetailID) REFERENCES PurchaseDetail(PurchaseDetailID) ON UPDATE CASCADE,
    FOREIGN KEY (ProductID)        REFERENCES Product(ProductID)              ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 销售退货主表
DROP TABLE IF EXISTS SaleReturnOrder;
CREATE TABLE SaleReturnOrder (
    ReturnID        VARCHAR(20)     NOT NULL PRIMARY KEY,
    SaleID          VARCHAR(20)     NOT NULL,
    CustomerID      VARCHAR(20)     NOT NULL,
    WarehouseID     VARCHAR(20)     NOT NULL,
    ReturnDate      DATETIME,
    Status          VARCHAR(10)     DEFAULT '草稿',
    TotalAmount     DECIMAL(18,2)   DEFAULT 0,
    Operator        VARCHAR(20),
    ReturnOperator  VARCHAR(20),
    RollbackDate    DATETIME,
    RollbackOperator VARCHAR(20),
    Remark          TEXT,
    FOREIGN KEY (SaleID)      REFERENCES SaleOrder(SaleID)       ON UPDATE CASCADE,
    FOREIGN KEY (CustomerID)  REFERENCES Customer(CustomerID)     ON UPDATE CASCADE,
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID)  ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 销售退货明细
DROP TABLE IF EXISTS SaleReturnDetail;
CREATE TABLE SaleReturnDetail (
    ReturnDetailID    VARCHAR(20)   NOT NULL PRIMARY KEY,
    ReturnID          VARCHAR(20)   NOT NULL,
    SaleDetailID      VARCHAR(20)   NOT NULL,
    ProductID         VARCHAR(20)   NOT NULL,
    Quantity          DECIMAL(18,2) DEFAULT 0,
    UnitPrice         DECIMAL(18,2) DEFAULT 0,
    Amount            DECIMAL(18,2) DEFAULT 0,
    FOREIGN KEY (ReturnID)    REFERENCES SaleReturnOrder(ReturnID) ON UPDATE CASCADE,
    FOREIGN KEY (SaleDetailID) REFERENCES SaleDetail(SaleDetailID) ON UPDATE CASCADE,
    FOREIGN KEY (ProductID)   REFERENCES Product(ProductID)        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 盘点单主表
DROP TABLE IF EXISTS StockCheckOrder;
CREATE TABLE StockCheckOrder (
    CheckID         VARCHAR(20)     NOT NULL PRIMARY KEY,
    WarehouseID     VARCHAR(20)     NOT NULL,
    CheckDate       DATETIME,
    Status          VARCHAR(10)     DEFAULT '草稿',
    Operator        VARCHAR(20),
    AuditOperator   VARCHAR(20),
    AuditDate       DATETIME,
    RollbackDate    DATETIME,
    RollbackOperator VARCHAR(20),
    Remark          TEXT,
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 盘点明细
DROP TABLE IF EXISTS StockCheckDetail;
CREATE TABLE StockCheckDetail (
    CheckDetailID   VARCHAR(20)     NOT NULL PRIMARY KEY,
    CheckID         VARCHAR(20)     NOT NULL,
    ProductID       VARCHAR(20)     NOT NULL,
    BookQuantity    DECIMAL(18,2)   DEFAULT 0,
    ActualQuantity  DECIMAL(18,2)   DEFAULT 0,
    DiffQuantity    DECIMAL(18,2)   DEFAULT 0,
    UnitPrice       DECIMAL(18,2)   DEFAULT 0,
    Remark          TEXT,
    FOREIGN KEY (CheckID)   REFERENCES StockCheckOrder(CheckID) ON UPDATE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)       ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 损益单主表
DROP TABLE IF EXISTS ProfitLossOrder;
CREATE TABLE ProfitLossOrder (
    ProfitLossID    VARCHAR(20)     NOT NULL PRIMARY KEY,
    WarehouseID     VARCHAR(20)     NOT NULL,
    OrderDate       DATETIME,
    Type            VARCHAR(10)     NOT NULL COMMENT '盘盈/盘亏',
    Status          VARCHAR(10)     DEFAULT '草稿',
    TotalAmount     DECIMAL(18,2)   DEFAULT 0,
    Operator        VARCHAR(20),
    AuditOperator   VARCHAR(20),
    AuditDate       DATETIME,
    RollbackDate    DATETIME,
    RollbackOperator VARCHAR(20),
    Remark          TEXT,
    CheckID         VARCHAR(20),
    FOREIGN KEY (WarehouseID) REFERENCES Warehouse(WarehouseID)   ON UPDATE CASCADE,
    FOREIGN KEY (CheckID)     REFERENCES StockCheckOrder(CheckID) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 损益明细
DROP TABLE IF EXISTS ProfitLossDetail;
CREATE TABLE ProfitLossDetail (
    ProfitLossDetailID VARCHAR(20)   NOT NULL PRIMARY KEY,
    ProfitLossID       VARCHAR(20)   NOT NULL,
    ProductID          VARCHAR(20)   NOT NULL,
    Quantity           DECIMAL(18,2) DEFAULT 0,
    UnitPrice          DECIMAL(18,2) DEFAULT 0,
    Amount             DECIMAL(18,2) DEFAULT 0,
    BatchID            VARCHAR(20),
    Remark             TEXT,
    FOREIGN KEY (ProfitLossID) REFERENCES ProfitLossOrder(ProfitLossID) ON UPDATE CASCADE,
    FOREIGN KEY (ProductID)    REFERENCES Product(ProductID)            ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
