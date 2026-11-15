"""Create a small demo account and sample history for local exploration."""
from datetime import date, timedelta
from sqlalchemy import select
from app.db import Base, SessionLocal, engine
from app.models import User, Transaction, Budget
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    user=db.scalar(select(User).where(User.email=="demo@spendsense.local"))
    if user is None:
        user=User(name="Demo User",email="demo@spendsense.local",password_hash=hash_password("demo-password"))
        db.add(user);db.commit();db.refresh(user)
    if not db.scalar(select(Transaction.id).where(Transaction.user_id==user.id).limit(1)):
        today=date.today()
        samples=[
            (0,4200,"income","Other","Campus stipend","Monthly stipend"),
            (1,180,"expense","Food & Dining","Green Bowl","Lunch with friends"),
            (2,75,"expense","Transportation","Metro","Metro ride"),
            (4,899,"expense","Entertainment","Streamly","Monthly subscription"),
            (6,640,"expense","Food & Dining","Corner Cafe","Coffee and breakfast"),
            (9,1250,"expense","Shopping","Bookshop","Course books"),
            (12,320,"expense","Bills & Utilities","Mobile","Monthly recharge"),
            (16,540,"expense","Food & Dining","Dosa House","Dinner"),
        ]
        for days,amount,kind,category,merchant,description in samples:
            db.add(Transaction(user_id=user.id,date=today-timedelta(days=days),amount=amount,type=kind,category=category,merchant=merchant,description=description,payment_method="UPI"))
        month=today.strftime("%Y-%m")
        db.add(Budget(user_id=user.id,month=month,category="All categories",amount=12000))
        db.add(Budget(user_id=user.id,month=month,category="Food & Dining",amount=3000))
        db.commit()
    print("Demo ready: demo@spendsense.local / demo-password")
finally:
    db.close()
