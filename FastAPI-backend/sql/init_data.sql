-- 初始数据

START TRANSACTION;

-- 1. 插入商品类型 (Category)
INSERT INTO Category (CategoryID, CategoryName, Description) VALUES
('C001', '电子产品', '手机、电脑、平板等'),
('C002', '办公用品', '纸张、笔、文件夹等'),
('C003', '食品饮料', '零食、矿泉水等');

-- 2. 插入仓库 (Warehouse)
INSERT INTO Warehouse (WarehouseID, WarehouseName, Location, Phone) VALUES
('WH001', '北京总仓', '北京市大兴区', '010-88880001'),
('WH002', '上海分仓', '上海市浦东新区', '021-88880002'),
('WH003', '广州分仓', '广州市天河区', '020-88880003');

-- 3. 插入供应商 (Supplier)
INSERT INTO Supplier (SupplierID, SupplierName, Contact, Phone, Address) VALUES
('SUP001', '联想科技有限公司', '张经理', '13800000001', '北京市海淀区'),
('SUP002', '晨光文具批发商', '李小姐', '13800000002', '上海市静安区'),
('SUP003', '农夫山泉股份', '王先生', '13800000003', '浙江省杭州市');

-- 4. 插入客户 (Customer)
INSERT INTO Customer (CustomerID, CustomerName, Contact, Phone, Address) VALUES
('CUS001', '阿里巴巴集团', '赵采购', '13900000001', '杭州市余杭区'),
('CUS002', '腾讯科技', '钱采购', '13900000002', '深圳市南山区'),
('CUS003', '字节跳动', '孙采购', '13900000003', '北京市海淀区');

-- 5. 插入商品 (Product)
INSERT INTO Product (ProductID, CategoryID, ProductName, Spec, Unit, Remark) VALUES
('P001', 'C001', 'ThinkPad X1 笔记本', '16GB/512GB', '台', '高端商务本'),
('P002', 'C001', 'iPhone 15 Pro', '256GB 黑色', '台', '旗舰手机'),
('P003', 'C002', '晨光中性笔', '0.5mm 黑色', '支', '办公常备'),
('P004', 'C002', 'A4打印纸', '80g 500张/包', '包', '双面打印'),
('P005', 'C003', '农夫山泉矿泉水', '550ml 24瓶/箱', '箱', '会议用水');

-- 6. 插入商品供应商关联 (ProductSupplier)
INSERT INTO ProductSupplier (ProductSupplierID, ProductID, SupplierID, SupplyPrice) VALUES
('PS001', 'P001', 'SUP001', 8500.00),
('PS002', 'P003', 'SUP002', 2.50),
('PS003', 'P004', 'SUP002', 25.00),
('PS004', 'P005', 'SUP003', 30.00),
('PS005', 'P002', 'SUP001', 6800.00);

-- 7. 初始化库存总表 (TotalStock)
INSERT INTO TotalStock (ProductID, TotalQuantity, AveragePrice, LastPurchasePrice, LastUpdated) VALUES
('P001', 50, 8500.00, 8500.00, NOW()),
('P002', 30, 6800.00, 6800.00, NOW()),
('P003', 1000, 2.50, 2.50, NOW()),
('P004', 200, 25.00, 25.00, NOW()),
('P005', 500, 30.00, 30.00, NOW());

-- 8. 初始化仓库库存表 (WarehouseStock)
INSERT INTO WarehouseStock (ProductID, WarehouseID, Quantity, LastUpdated) VALUES
('P001', 'WH001', 30, NOW()),
('P002', 'WH001', 20, NOW()),
('P003', 'WH001', 500, NOW()),
('P004', 'WH001', 100, NOW()),
('P005', 'WH001', 300, NOW()),
('P001', 'WH002', 20, NOW()),
('P002', 'WH002', 10, NOW()),
('P003', 'WH002', 300, NOW()),
('P004', 'WH002', 100, NOW()),
('P005', 'WH002', 200, NOW()),
('P001', 'WH003', 0, NOW());


COMMIT;
