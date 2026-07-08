from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from ..database import get_db
from ..models import Product, ProductSupplier
from ..schemas import ProductCreate, ProductUpdate, ProductOut, ProductInfoOut, ProductSupplierCreate, ProductSupplierOut

router = APIRouter(prefix="/api/products", tags=["商品"])


@router.get("/", response_model=List[ProductInfoOut])
def list_products(db: Session = Depends(get_db)):
    """通过视图获取商品信息（含类型名称和库存）"""
    result = db.execute(text("SELECT * FROM vw_ProductInfo")).mappings().all()
    return [dict(r) for r in result]


@router.get("/{prod_id}", response_model=ProductInfoOut)
def get_product(prod_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("SELECT * FROM vw_ProductInfo WHERE ProductID = :pid"),
        {"pid": prod_id}
    ).mappings().first()
    if not result:
        raise HTTPException(status_code=404, detail="商品不存在")
    return dict(result)


@router.post("/", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.ProductID == data.ProductID).first():
        raise HTTPException(status_code=400, detail="商品编号已存在")
    prod = Product(**data.model_dump())
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


@router.put("/{prod_id}", response_model=ProductOut)
def update_product(prod_id: str, data: ProductUpdate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.ProductID == prod_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="商品不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(prod, key, val)
    db.commit()
    db.refresh(prod)
    return prod


@router.delete("/{prod_id}")
def delete_product(prod_id: str, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.ProductID == prod_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.delete(prod)
    db.commit()
    return {"message": "删除成功"}


# --- 商品供应商关联 ---
@router.get("/{prod_id}/suppliers", response_model=List[ProductSupplierOut])
def get_product_suppliers(prod_id: str, db: Session = Depends(get_db)):
    return db.query(ProductSupplier).filter(ProductSupplier.ProductID == prod_id).all()


@router.post("/suppliers", response_model=ProductSupplierOut)
def add_product_supplier(data: ProductSupplierCreate, db: Session = Depends(get_db)):
    if db.query(ProductSupplier).filter(
        ProductSupplier.ProductSupplierID == data.ProductSupplierID
    ).first():
        raise HTTPException(status_code=400, detail="关联编号已存在")
    ps = ProductSupplier(**data.model_dump())
    db.add(ps)
    db.commit()
    db.refresh(ps)
    return ps


@router.delete("/suppliers/{ps_id}")
def remove_product_supplier(ps_id: str, db: Session = Depends(get_db)):
    ps = db.query(ProductSupplier).filter(ProductSupplier.ProductSupplierID == ps_id).first()
    if not ps:
        raise HTTPException(status_code=404, detail="关联不存在")
    db.delete(ps)
    db.commit()
    return {"message": "删除成功"}
