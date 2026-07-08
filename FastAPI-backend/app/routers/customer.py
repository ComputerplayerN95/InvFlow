from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Customer
from ..schemas import CustomerCreate, CustomerUpdate, CustomerOut

router = APIRouter(prefix="/api/customers", tags=["客户"])


@router.get("/", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@router.get("/{cus_id}", response_model=CustomerOut)
def get_customer(cus_id: str, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.CustomerID == cus_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    return c


@router.post("/", response_model=CustomerOut)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    if db.query(Customer).filter(Customer.CustomerID == data.CustomerID).first():
        raise HTTPException(status_code=400, detail="客户编号已存在")
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/{cus_id}", response_model=CustomerOut)
def update_customer(cus_id: str, data: CustomerUpdate, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.CustomerID == cus_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(c, key, val)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{cus_id}")
def delete_customer(cus_id: str, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.CustomerID == cus_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    db.delete(c)
    db.commit()
    return {"message": "删除成功"}
