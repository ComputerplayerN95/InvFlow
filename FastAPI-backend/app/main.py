from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import APP_TITLE, APP_VERSION, HOST, PORT
from .routers import (
    category, warehouse, supplier, customer, product,
    purchase, sale, transfer, stock, reports,
)
import os

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(category.router)
app.include_router(warehouse.router)
app.include_router(supplier.router)
app.include_router(customer.router)
app.include_router(product.router)
app.include_router(purchase.router)
app.include_router(sale.router)
app.include_router(transfer.router)
app.include_router(stock.router)
app.include_router(reports.router)

# 注册前端静态文件（开发时用 npm run dev，部署时用 npm run build）
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "vue-frontend", "dist")

@app.get("/api/health")
def health():
    return {"app": APP_TITLE, "version": APP_VERSION, "status": "ok"}

# 静态文件挂载必须在所有路由之后
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
