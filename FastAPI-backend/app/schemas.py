from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== 基础数据 Schema ====================
class CategoryCreate(BaseModel):
    CategoryID: str
    CategoryName: str
    Description: Optional[str] = None

class CategoryUpdate(BaseModel):
    CategoryName: Optional[str] = None
    Description: Optional[str] = None

class CategoryOut(BaseModel):
    CategoryID: str
    CategoryName: str
    Description: Optional[str] = None
    class Config: from_attributes = True


class WarehouseCreate(BaseModel):
    WarehouseID: str
    WarehouseName: str
    Location: Optional[str] = None
    Phone: Optional[str] = None

class WarehouseUpdate(BaseModel):
    WarehouseName: Optional[str] = None
    Location: Optional[str] = None
    Phone: Optional[str] = None

class WarehouseOut(BaseModel):
    WarehouseID: str
    WarehouseName: str
    Location: Optional[str] = None
    Phone: Optional[str] = None
    class Config: from_attributes = True


class SupplierCreate(BaseModel):
    SupplierID: str
    SupplierName: str
    Contact: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None

class SupplierUpdate(BaseModel):
    SupplierName: Optional[str] = None
    Contact: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None

class SupplierOut(BaseModel):
    SupplierID: str
    SupplierName: str
    Contact: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None
    class Config: from_attributes = True


class CustomerCreate(BaseModel):
    CustomerID: str
    CustomerName: str
    Contact: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None

class CustomerUpdate(BaseModel):
    CustomerName: Optional[str] = None
    Contact: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None

class CustomerOut(BaseModel):
    CustomerID: str
    CustomerName: str
    Contact: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None
    class Config: from_attributes = True


class ProductCreate(BaseModel):
    ProductID: str
    CategoryID: str
    ProductName: str
    Spec: Optional[str] = None
    Unit: Optional[str] = None
    Remark: Optional[str] = None

class ProductUpdate(BaseModel):
    CategoryID: Optional[str] = None
    ProductName: Optional[str] = None
    Spec: Optional[str] = None
    Unit: Optional[str] = None
    Remark: Optional[str] = None

class ProductOut(BaseModel):
    ProductID: str
    CategoryID: str
    ProductName: str
    Spec: Optional[str] = None
    Unit: Optional[str] = None
    Remark: Optional[str] = None
    class Config: from_attributes = True

# 商品视图（含类型名称、库存信息）
class ProductInfoOut(BaseModel):
    ProductID: str
    ProductName: str
    Spec: Optional[str] = None
    Unit: Optional[str] = None
    Remark: Optional[str] = None
    CategoryID: Optional[str] = None
    CategoryName: Optional[str] = None
    TotalQuantity: Optional[float] = None
    AveragePrice: Optional[float] = None
    LastPurchasePrice: Optional[float] = None
    class Config: from_attributes = True


class ProductSupplierCreate(BaseModel):
    ProductSupplierID: str
    ProductID: str
    SupplierID: str
    SupplyPrice: Optional[float] = None

class ProductSupplierOut(BaseModel):
    ProductSupplierID: str
    ProductID: str
    SupplierID: str
    SupplyPrice: Optional[float] = None
    class Config: from_attributes = True


# ==================== 采购单 Schema ====================
class PurchaseDetailItem(BaseModel):
    PurchaseDetailID: str
    ProductID: str
    Quantity: float
    UnitPrice: float
    Amount: float

class PurchaseOrderCreate(BaseModel):
    PurchaseID: str
    SupplierID: str
    WarehouseID: str
    OrderDate: Optional[datetime] = None
    Operator: Optional[str] = None
    Details: List[PurchaseDetailItem] = []

class PurchaseOrderUpdate(BaseModel):
    SupplierID: Optional[str] = None
    WarehouseID: Optional[str] = None
    OrderDate: Optional[datetime] = None
    Operator: Optional[str] = None
    Details: Optional[List[PurchaseDetailItem]] = None  # 新增

class PurchaseOrderOut(BaseModel):
    PurchaseID: str
    SupplierID: str
    WarehouseID: str
    OrderDate: Optional[datetime] = None
    Status: str = "草稿"
    TotalAmount: Optional[float] = 0
    Operator: Optional[str] = None
    InDate: Optional[datetime] = None
    InOperator: Optional[str] = None
    class Config: from_attributes = True

class PurchaseDetailOut(BaseModel):
    PurchaseDetailID: str
    PurchaseID: str
    ProductID: str
    Quantity: float
    UnitPrice: float
    Amount: float
    class Config: from_attributes = True

class PurchaseOrderFullOut(PurchaseOrderOut):
    SupplierName: Optional[str] = None
    WarehouseName: Optional[str] = None
    Details: List[PurchaseDetailOut] = []
    RollbackDate: Optional[datetime] = None
    RollbackOperator: Optional[str] = None


# ==================== 销售单 Schema ====================
class SaleDetailItem(BaseModel):
    SaleDetailID: str
    ProductID: str
    Quantity: float
    UnitPrice: float
    Amount: float

class SaleOrderCreate(BaseModel):
    SaleID: str
    CustomerID: str
    WarehouseID: str
    OrderDate: Optional[datetime] = None
    Operator: Optional[str] = None
    Details: List[SaleDetailItem] = []

class SaleOrderUpdate(BaseModel):
    CustomerID: Optional[str] = None
    WarehouseID: Optional[str] = None
    OrderDate: Optional[datetime] = None
    Operator: Optional[str] = None
    Details: Optional[List[SaleDetailItem]] = None  # 新增

class SaleOrderOut(BaseModel):
    SaleID: str
    CustomerID: str
    WarehouseID: str
    OrderDate: Optional[datetime] = None
    Status: str = "草稿"
    TotalAmount: Optional[float] = 0
    Operator: Optional[str] = None
    OutDate: Optional[datetime] = None
    OutOperator: Optional[str] = None
    class Config: from_attributes = True

class SaleDetailOut(BaseModel):
    SaleDetailID: str
    SaleID: str
    ProductID: str
    Quantity: float
    UnitPrice: float
    Amount: float
    class Config: from_attributes = True

class SaleOrderFullOut(SaleOrderOut):
    CustomerName: Optional[str] = None
    WarehouseName: Optional[str] = None
    Details: List[SaleDetailOut] = []
    RollbackDate: Optional[datetime] = None
    RollbackOperator: Optional[str] = None


# ==================== 调拨单 Schema ====================
class TransferDetailItem(BaseModel):
    TransferDetailID: str
    ProductID: str
    Quantity: float

class TransferOrderCreate(BaseModel):
    TransferID: str
    FromWarehouseID: str
    ToWarehouseID: str
    OrderDate: Optional[datetime] = None
    Operator: Optional[str] = None
    Details: List[TransferDetailItem] = []

class TransferOrderUpdate(BaseModel):
    FromWarehouseID: Optional[str] = None
    ToWarehouseID: Optional[str] = None
    OrderDate: Optional[datetime] = None
    Operator: Optional[str] = None

class TransferOrderOut(BaseModel):
    TransferID: str
    FromWarehouseID: str
    ToWarehouseID: str
    OrderDate: Optional[datetime] = None
    Status: str = "草稿"
    Operator: Optional[str] = None
    class Config: from_attributes = True

class TransferDetailOut(BaseModel):
    TransferDetailID: str
    TransferID: str
    ProductID: str
    Quantity: float
    class Config: from_attributes = True

class TransferOrderFullOut(TransferOrderOut):
    FromWarehouseName: Optional[str] = None
    ToWarehouseName: Optional[str] = None
    Details: List[TransferDetailOut] = []


# ==================== 库存 Schema ====================
class TotalStockOut(BaseModel):
    ProductID: str
    ProductName: Optional[str] = None
    TotalQuantity: Optional[float] = 0
    AveragePrice: Optional[float] = 0
    LastPurchasePrice: Optional[float] = 0
    LastUpdated: Optional[datetime] = None
    class Config: from_attributes = True

class WarehouseStockOut(BaseModel):
    ProductID: str
    WarehouseID: str
    ProductName: Optional[str] = None
    WarehouseName: Optional[str] = None
    Quantity: Optional[float] = 0
    LastUpdated: Optional[datetime] = None
    class Config: from_attributes = True


# ==================== 报表 Schema ====================
class MonthlyStockOut(BaseModel):
    MonthlyStockID: str
    ProductID: str
    YearMonth: str
    BeginQty: Optional[float] = 0
    BeginAmount: Optional[float] = 0
    InQty: Optional[float] = 0
    InAmount: Optional[float] = 0
    OutQty: Optional[float] = 0
    OutAmount: Optional[float] = 0
    EndQty: Optional[float] = 0
    EndAmount: Optional[float] = 0
    ProductName: Optional[str] = None
    CategoryName: Optional[str] = None
    class Config: from_attributes = True

class MonthlySettlementRequest(BaseModel):
    YearMonth: str  # YYYY-MM
    Operator: str

class AntiSettlementRequest(BaseModel):
    YearMonth: str  # YYYY-MM


# ==================== 通用响应 ====================
class MessageResponse(BaseModel):
    message: str
    success: bool = True
