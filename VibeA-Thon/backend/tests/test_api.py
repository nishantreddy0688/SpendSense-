import pytest
from fastapi import HTTPException
from datetime import date
from app.db import Base
from app.models import User
from app.schemas import Register, Login, TransactionIn, BudgetIn
from app.main import register, login, create_transaction, update_transaction, delete_transaction, owned_transaction, create_budget, list_budgets
from test_services import database

def test_auth_transaction_crud_and_user_isolation():
    db=database()
    token_data=register(Register(name="Test User",email="api-a@example.com",password="secure-pass-123"),db)
    a=token_data["user"]
    assert token_data["access_token"] and a.password_hash!="secure-pass-123"
    assert login(Login(email=a.email,password="secure-pass-123"),db)["user"]==a
    tx=create_transaction(TransactionIn(amount=220,type="expense",category="Food & Dining",merchant="Cafe"),db,a)
    assert tx.id and tx.user_id==a.id
    update_transaction(tx.id,TransactionIn(amount=260,type="expense",category="Shopping",merchant="Bookshop"),db,a)
    assert owned_transaction(tx.id,db,a).amount==260
    month=date.today().strftime("%Y-%m")
    create_budget(BudgetIn(month=month,category="Shopping",amount=400),db,a)
    assert list_budgets(db,a)[0]["spent"]==260
    b=User(name="Other User",email="api-b@example.com",password_hash="hashed");db.add(b);db.commit()
    with pytest.raises(HTTPException) as exc: owned_transaction(tx.id,db,b)
    assert exc.value.status_code==404
    delete_transaction(tx.id,db,a)
    with pytest.raises(HTTPException): owned_transaction(tx.id,db,a)
