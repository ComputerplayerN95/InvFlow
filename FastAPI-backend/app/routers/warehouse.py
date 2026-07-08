from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Warehouse
from ..schemas import WarehouseCreate, WarehouseUpdate, WarehouseOut

router = APIRouter(prefix="/api/warehouses", tags=["仓库"])


@router.get("/", response_model=List[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).all()


@router.get("/{wh_id}", response_model=WarehouseOut)
def get_warehouse(wh_id: str, db: Session = Depends(get_db)):
    wh = db.query(Warehouse).filter(Warehouse.WarehouseID == wh_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    return wh


@router.post("/", response_model=WarehouseOut)
def create_warehouse(data: WarehouseCreate, db: Session = Depends(get_db)):
    if db.query(Warehouse).filter(Warehouse.WarehouseID == data.WarehouseID).first():
        raise HTTPException(status_code=400, detail="仓库编号已存在")
    wh = Warehouse(**data.model_dump())
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.put("/{wh_id}", response_model=WarehouseOut)
def update_warehouse(wh_id: str, data: WarehouseUpdate, db: Session = Depends(get_db)):
    wh = db.query(Warehouse).filter(Warehouse.WarehouseID == wh_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(wh, key, val)
    db.commit()
    db.refresh(wh)
    return wh


@router.delete("/{wh_id}")
def delete_warehouse(wh_id: str, db: Session = Depends(get_db)):
    wh = db.query(Warehouse).filter(Warehouse.WarehouseID == wh_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    db.delete(wh)
    db.commit()
    return {"message": "删除成功"}
