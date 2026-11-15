from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base
from app.models import User, Transaction
from app.services import categorize, monthly_summary, parse_text, insights
from app.main import forecast
from app.statement_import import _gpay_rows

def database():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def test_categorization_and_uncertainty():
    assert categorize("Lunch at cafe")["category"]=="Food & Dining"
    assert categorize("misc note")["confidence"]<0.5

def test_natural_language_parse_never_saves():
    parsed=parse_text("I spent 180 rupees on lunch today")
    assert parsed["amount"]==180
    assert parsed["type"]=="expense"
    assert parsed["category"]=="Food & Dining"
    assert parse_text("Lunch today")["needs_clarification"] is True

def test_monthly_summary_uses_user_transactions():
    db=database();u=User(name="A",email="a@example.com",password_hash="hashed");db.add(u);db.commit()
    db.add_all([Transaction(user_id=u.id,date=date.today(),amount=200,type="expense",category="Food & Dining"),Transaction(user_id=u.id,date=date.today(),amount=1000,type="income",category="Other")]);db.commit()
    s=monthly_summary(db,u.id)
    assert s["expenses"]==200 and s["income"]==1000 and s["savings"]==800
    assert s["categories"][0]["category"]=="Food & Dining"

def test_insights_derive_from_transaction_data():
    db=database();u=User(name="A",email="b@example.com",password_hash="hashed");db.add(u);db.commit()
    db.add(Transaction(user_id=u.id,date=date.today(),amount=500,type="expense",category="Travel",merchant="Train"));db.commit()
    result=insights(db,u.id)
    assert "Travel" in result[0]["title"] and "₹500" in result[0]["detail"]

def test_anomaly_uses_iqr_baseline():
    db=database();u=User(name="A",email="outlier@example.com",password_hash="hashed");db.add(u);db.commit()
    for amount in [100,110,120,130,1200]: db.add(Transaction(user_id=u.id,date=date.today(),amount=amount,type="expense",category="Shopping",merchant="Store"))
    db.commit()
    found=[x for x in insights(db,u.id) if x["kind"]=="anomaly"]
    assert found and "IQR" in found[0]["detail"]

def test_forecast_requires_history_and_uses_moving_average():
    db=database();u=User(name="A",email="forecast@example.com",password_hash="hashed");db.add(u);db.commit()
    assert forecast(db,u)["available"] is False
    months=[]
    y,m=date.today().year,date.today().month-1
    if m==0:y-=1;m=12
    for amount in [100,200,300]:
        months.append((y,m,amount));m-=1
        if m==0:y-=1;m=12
    for y,m,amount in months:db.add(Transaction(user_id=u.id,date=date(y,m,5),amount=amount,type="expense",category="Other"))
    db.commit()
    result=forecast(db,u)
    assert result["available"] and result["method"]=="3-month moving average using completed months" and result["predicted"]==200

def test_google_pay_statement_rows_parse_income_expenses_and_duplicate_ids():
    text="""Transaction statement
Date & time Transaction details Amount
02 Aug, 2026
07:23PM
Paid to Anvi distributors iit 2
UPITransactionID:621403747274
PaidbyStateBankofIndia0800
₹207
03 Aug, 2026
07:16PM
Received from MANASWI DILIP GHODAKE
UPITransactionID:392365695345
PaidtoStateBankofIndia0800
₹207
04 Aug, 2026
06:34PM
Paid to IIT CANTEEN MESS
UPITransactionID:621624578329
PaidbyStateBankofIndia0800
₹85"""
    rows=_gpay_rows([text],"statement-hash")
    assert len(rows)==3
    assert rows[0]["date"]=="2026-08-02" and rows[0]["amount"]==207 and rows[0]["type"]=="expense"
    assert rows[0]["source_ref"]=="id:621403747274" and rows[0]["payment_method"]=="UPI"
    assert rows[1]["type"]=="income" and rows[1]["merchant"]=="MANASWI DILIP GHODAKE"
    assert rows[2]["category"]=="Food & Dining"
