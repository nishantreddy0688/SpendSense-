import re
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, pstdev
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Transaction, Budget

CATEGORIES = ["Food & Dining", "Transportation", "Shopping", "Education", "Entertainment", "Health", "Bills & Utilities", "Personal Care", "Travel", "Other"]
RULES = {"Food & Dining":["lunch","dinner","breakfast","restaurant","cafe","food","swiggy","zomato"],"Transportation":["uber","ola","metro","bus","fuel","petrol","cab"],"Shopping":["amazon","flipkart","shopping","clothes","myntra"],"Education":["course","books","tuition","college","udemy"],"Entertainment":["movie","netflix","spotify","concert","game"],"Health":["pharmacy","doctor","hospital","medicine","clinic"],"Bills & Utilities":["electricity","water bill","internet","recharge","rent","bill"],"Travel":["flight","hotel","train","booking","travel"]}
def categorize(text: str):
    value=text.lower()
    for category, words in RULES.items():
        if any(w in value for w in words): return {"category":category,"confidence":0.88,"method":"rules"}
    return {"category":"Other","confidence":0.35,"method":"rules"}
def monthly_summary(db: Session, user_id: int):
    month=date.today().strftime("%Y-%m")
    rows=db.scalars(select(Transaction).where(Transaction.user_id==user_id, Transaction.date>=date.today().replace(day=1))).all()
    income=sum(x.amount for x in rows if x.type=="income"); expense=sum(x.amount for x in rows if x.type=="expense")
    budgets=db.scalars(select(Budget).where(Budget.user_id==user_id,Budget.month==month)).all()
    limit=sum(x.amount for x in budgets)
    cats=defaultdict(float)
    for x in rows:
        if x.type=="expense": cats[x.category]+=x.amount
    days=max(date.today().day,1)
    return {"month":month,"income":income,"expenses":expense,"savings":income-expense,"savings_rate":round((income-expense)/income*100,1) if income else 0,"budget":limit,"remaining_budget":limit-expense if limit else None,"categories":[{"category":k,"amount":v} for k,v in sorted(cats.items(),key=lambda p:p[1],reverse=True)],"daily":[{"day":(date.today()-timedelta(days=i)).isoformat(),"amount":sum(t.amount for t in rows if t.type=="expense" and t.date==date.today()-timedelta(days=i))} for i in reversed(range(min(days,14)))],"recent":[{"id":t.id,"date":t.date.isoformat(),"amount":t.amount,"type":t.type,"category":t.category,"merchant":t.merchant,"description":t.description} for t in sorted(rows,key=lambda t:(t.date,t.id),reverse=True)[:6]]}
def parse_text(text: str):
    low=text.lower(); m=re.search(r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)\s*(?:rupees?|inr)?",low)
    if not m: return {"needs_clarification":True,"reason":"I couldn't find an amount. Add the amount before continuing."}
    amount=float(m.group(1).replace(",","")); typ="income" if any(w in low for w in ["received","salary","stipend","earned","refund"]) else "expense"
    when=date.today();
    if "yesterday" in low: when-=timedelta(days=1)
    cat=categorize(low)
    remove=[m.group(0),"today","yesterday","spent","paid","received","rupees","rupee","for","on","as"]
    merchant=low
    for word in remove: merchant=re.sub(r"\b"+re.escape(word)+r"\b","",merchant)
    merchant=re.sub(r"\s+"," ",merchant).strip(" .") or "Personal"
    return {"amount":amount,"date":when.isoformat(),"type":typ,"category":cat["category"],"merchant":merchant.title(),"description":text,"confidence":cat["confidence"],"needs_clarification":False}
def insights(db: Session, user_id: int):
    rows=db.scalars(select(Transaction).where(Transaction.user_id==user_id,Transaction.type=="expense")).all()
    result=[]
    if not rows: return [{"title":"Start with your first transaction","detail":"Add a few expenses to see patterns drawn from your real spending history.","kind":"tip"}]
    sums=defaultdict(float)
    for t in rows:sums[t.category]+=t.amount
    total=sum(sums.values()); top=max(sums,key=sums.get)
    result.append({"title":f"{top} is your top category","detail":f"₹{sums[top]:,.0f} of ₹{total:,.0f} recorded expenses ({sums[top]/total*100:.0f}%) are in {top}.","kind":"category"})
    amounts=[x.amount for x in rows]
    if len(amounts)>=4:
        q=sorted(amounts)
        def quantile(p):
            pos=(len(q)-1)*p;lo=int(pos);hi=min(lo+1,len(q)-1)
            return q[lo]+(q[hi]-q[lo])*(pos-lo)
        q1,q3=quantile(.25),quantile(.75);med=q[len(q)//2];spread=pstdev(amounts)
        for t in sorted(rows,key=lambda x:x.amount,reverse=True):
            if t.amount>q3+1.5*(q3-q1) or t.amount>mean(amounts)+3*spread:
                result.append({"title":"Unusually large expense","detail":f"₹{t.amount:,.0f} at {t.merchant or t.category} is above the IQR outlier range in your history (typical expense around ₹{med:,.0f}). This is a spending anomaly, not a fraud determination.","kind":"anomaly","transaction_id":t.id}); break
    return result
