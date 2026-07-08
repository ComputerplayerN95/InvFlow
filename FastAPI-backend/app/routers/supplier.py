from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Supplier
from ..schemas import SupplierCreate, SupplierUpdate, SupplierOut

router = APIRouter(prefix="/api/suppliers", tags=["供应商"])


@router.get("/", response_model=List[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()


@router.get("/{sup_id}", response_model=SupplierOut)
def get_supplier(sup_id: str, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.SupplierID == sup_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return s


@router.post("/", response_model=SupplierOut)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    if db.query(Supplier).filter(Supplier.SupplierID == data.SupplierID).first():
        raise HTTPException(status_code=400, detail="供应商编号已存在")
    s = Supplier(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/{sup_id}", response_model=SupplierOut)
def update_supplier(sup_id: str, data: SupplierUpdate, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.SupplierID == sup_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(s, key, val)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{sup_id}")
def delete_supplier(sup_id: str, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.SupplierID == sup_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    db.delete(s)
    db.commit()
    return {"message": "删除成功"}
