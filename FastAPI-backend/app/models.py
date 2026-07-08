from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Category(Base):
    __tablename__ = "Category"
    CategoryID = Column(String(20), primary_key=True)
    CategoryName = Column(String(50), nullable=False)
    Description = Column(String(200))
    products = relationship("Product", back_populates="category")


class Warehouse(Base):
    __tablename__ = "Warehouse"
    WarehouseID = Column(String(20), primary_key=True)
    WarehouseName = Column(String(50), nullable=False)
    Location = Column(String(100))
    Phone = Column(String(20))


class Supplier(Base):
    __tablename__ = "Supplier"
    SupplierID = Column(String(20), primary_key=True)
    SupplierName = Column(String(50), nullable=False)
    Contact = Column(String(20))
    Phone = Column(String(20))
    Address = Column(String(100))


class Customer(Base):
    __tablename__ = "Customer"
    CustomerID = Column(String(20), primary_key=True)
    CustomerName = Column(String(50), nullable=False)
    Contact = Column(String(20))
    Phone = Column(String(20))
    Address = Column(String(100))


class Product(Base):
    __tablename__ = "Product"
    ProductID = Column(String(20), primary_key=True)
    CategoryID = Column(String(20), ForeignKey("Category.CategoryID", onupdate="CASCADE"), nullable=False)
    ProductName = Column(String(50), nullable=False)
    Spec = Column(String(50))
    Unit = Column(String(10))
    Remark = Column(String(200))
    category = relationship("Category", back_populates="products")


class ProductSupplier(Base):
    __tablename__ = "ProductSupplier"
    ProductSupplierID = Column(String(20), primary_key=True)
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), nullable=False)
    SupplierID = Column(String(20), ForeignKey("Supplier.SupplierID", onupdate="CASCADE"), nullable=False)
    SupplyPrice = Column(Numeric(18, 2))


class TotalStock(Base):
    __tablename__ = "TotalStock"
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), primary_key=True)
    TotalQuantity = Column(Numeric(18, 2), default=0)
    AveragePrice = Column(Numeric(18, 2), default=0)
    LastPurchasePrice = Column(Numeric(18, 2), default=0)
    LastUpdated = Column(DateTime)


class WarehouseStock(Base):
    __tablename__ = "WarehouseStock"
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), primary_key=True)
    WarehouseID = Column(String(20), ForeignKey("Warehouse.WarehouseID", onupdate="CASCADE"), primary_key=True)
    Quantity = Column(Numeric(18, 2), default=0)
    LastUpdated = Column(DateTime)


class MonthlyStock(Base):
    __tablename__ = "MonthlyStock"
    MonthlyStockID = Column(String(20), primary_key=True)
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), nullable=False)
    YearMonth = Column(String(7), nullable=False)
    BeginQty = Column(Numeric(18, 2), default=0)
    BeginAmount = Column(Numeric(18, 2), default=0)
    InQty = Column(Numeric(18, 2), default=0)
    InAmount = Column(Numeric(18, 2), default=0)
    OutQty = Column(Numeric(18, 2), default=0)
    OutAmount = Column(Numeric(18, 2), default=0)
    EndQty = Column(Numeric(18, 2), default=0)
    EndAmount = Column(Numeric(18, 2), default=0)


class PurchaseOrder(Base):
    __tablename__ = "PurchaseOrder"
    PurchaseID = Column(String(20), primary_key=True)
    SupplierID = Column(String(20), ForeignKey("Supplier.SupplierID", onupdate="CASCADE"), nullable=False)
    WarehouseID = Column(String(20), ForeignKey("Warehouse.WarehouseID", onupdate="CASCADE"), nullable=False)
    OrderDate = Column(DateTime)
    Status = Column(String(10), default="草稿")
    TotalAmount = Column(Numeric(18, 2), default=0)
    Operator = Column(String(20))
    InDate = Column(DateTime)
    InOperator = Column(String(20))
    RollbackDate = Column(DateTime, nullable=True, comment='回退时间')
    RollbackOperator = Column(String(20), nullable=True, comment='回退操作人')


class PurchaseDetail(Base):
    __tablename__ = "PurchaseDetail"
    PurchaseDetailID = Column(String(20), primary_key=True)
    PurchaseID = Column(String(20), ForeignKey("PurchaseOrder.PurchaseID", onupdate="CASCADE"), nullable=False)
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), nullable=False)
    Quantity = Column(Numeric(18, 2), default=0)
    UnitPrice = Column(Numeric(18, 2), default=0)
    Amount = Column(Numeric(18, 2), default=0)


class SaleOrder(Base):
    __tablename__ = "SaleOrder"
    SaleID = Column(String(20), primary_key=True)
    CustomerID = Column(String(20), ForeignKey("Customer.CustomerID", onupdate="CASCADE"), nullable=False)
    WarehouseID = Column(String(20), ForeignKey("Warehouse.WarehouseID", onupdate="CASCADE"), nullable=False)
    OrderDate = Column(DateTime)
    Status = Column(String(10), default="草稿")
    TotalAmount = Column(Numeric(18, 2), default=0)
    Operator = Column(String(20))
    OutDate = Column(DateTime)
    OutOperator = Column(String(20))
    RollbackDate = Column(DateTime, nullable=True, comment='回退时间')
    RollbackOperator = Column(String(20), nullable=True, comment='回退操作人')


class SaleDetail(Base):
    __tablename__ = "SaleDetail"
    SaleDetailID = Column(String(20), primary_key=True)
    SaleID = Column(String(20), ForeignKey("SaleOrder.SaleID", onupdate="CASCADE"), nullable=False)
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), nullable=False)
    Quantity = Column(Numeric(18, 2), default=0)
    UnitPrice = Column(Numeric(18, 2), default=0)
    Amount = Column(Numeric(18, 2), default=0)


class TransferOrder(Base):
    __tablename__ = "TransferOrder"
    TransferID = Column(String(20), primary_key=True)
    FromWarehouseID = Column(String(20), ForeignKey("Warehouse.WarehouseID", onupdate="CASCADE"), nullable=False)
    ToWarehouseID = Column(String(20), ForeignKey("Warehouse.WarehouseID", onupdate="CASCADE"), nullable=False)
    OrderDate = Column(DateTime)
    Status = Column(String(10), default="草稿")
    Operator = Column(String(20))


class TransferDetail(Base):
    __tablename__ = "TransferDetail"
    TransferDetailID = Column(String(20), primary_key=True)
    TransferID = Column(String(20), ForeignKey("TransferOrder.TransferID", onupdate="CASCADE"), nullable=False)
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), nullable=False)
    Quantity = Column(Numeric(18, 2), default=0)


class BatchStock(Base):
    __tablename__ = "BatchStock"
    BatchID = Column(String(20), primary_key=True)
    ProductID = Column(String(20), ForeignKey("Product.ProductID", onupdate="CASCADE"), nullable=False)
    WarehouseID = Column(String(20), nullable=False)
    PurchaseDetailID = Column(String(20))
    InDate = Column(DateTime, nullable=False)
    UnitPrice = Column(Numeric(18, 2), nullable=False)
    Quantity = Column(Numeric(18, 2), default=0)
    RemainingQty = Column(Numeric(18, 2), nullable=False)


class SaleOutBatch(Base):
    """FIFO出库批次明细——记录每笔销售从哪个FIFO批次扣的（7.1.2运维变更新增）"""
    __tablename__ = "SaleOutBatch"
    SaleOutBatchID = Column(String(30), primary_key=True)
    SaleDetailID = Column(String(20), ForeignKey("SaleDetail.SaleDetailID", onupdate="CASCADE"), nullable=False)
    BatchID = Column(String(20), ForeignKey("BatchStock.BatchID", onupdate="CASCADE"), nullable=False)
    Quantity = Column(Numeric(18, 2), nullable=False, comment='从该批次扣减的数量')
    UnitPrice = Column(Numeric(18, 2), nullable=False, comment='该批次的入库单价(FIFO成本)')
    OutDate = Column(DateTime, nullable=False, comment='出库时间')
