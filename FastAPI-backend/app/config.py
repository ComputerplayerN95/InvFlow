import os

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "invflow-db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 应用配置
APP_TITLE = "进销存管理系统"
APP_VERSION = "1.0.0"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# ID前缀
ID_PREFIX = {
    "category": "C",
    "warehouse": "WH",
    "supplier": "SUP",
    "customer": "CUS",
    "product": "P",
    "purchase": "PO",
    "purchase_detail": "PD",
    "sale": "SO",
    "sale_detail": "SD",
    "transfer": "TO",
    "transfer_detail": "TD",
    "monthly_stock": "MS",
    "product_supplier": "PS",
}
