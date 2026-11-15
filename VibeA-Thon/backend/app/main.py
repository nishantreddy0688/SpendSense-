from datetime import date
from statistics import pstdev
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import Base, engine, get_db
from app.models import User, Transaction, Budget
from app.schemas import Register, Login, Token, UserOut, TransactionIn, TransactionOut, BudgetIn, ParseRequest, PdfImportCommit
from app.security import hash_password, verify_password, make_token, current_user
from app.services import monthly_summary, categorize, parse_text, insights
from app.statement_import import parse_statement_pdf
import re

Base.metadata.create_all(bind=engine)
app=FastAPI(title="SpendSense API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/auth/register",response_model=Token,status_code=201)
def register(body:Register,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==body.email)): raise HTTPException(409,"Email already registered")
    u=User(name=body.name,email=body.email,password_hash=hash_password(body.password));db.add(u);db.commit();db.refresh(u);return {"access_token":make_token(u.id),"user":u}
@app.post("/auth/login",response_model=Token)
def login(body:Login,db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==body.email))
    if not u or not verify_password(body.password,u.password_hash): raise HTTPException(401,"Email or password is incorrect")
    return {"access_token":make_token(u.id),"user":u}
@app.post("/auth/logout")
def logout(user:User=Depends(current_user)):return {"message":"Signed out"}
@app.get("/auth/me",response_model=UserOut)
def me(user:User=Depends(current_user)):return user
@app.get("/transactions",response_model=list[TransactionOut])
def list_transactions(search:str|None=None,category:str|None=None,type:str|None=None,start:date|None=None,end:date|None=None,sort:str="date",db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Transaction).where(Transaction.user_id==user.id)
    if search:q=q.where(Transaction.description.ilike(f"%{search}%")|Transaction.merchant.ilike(f"%{search}%"))
    if category:q=q.where(Transaction.category==category)
    if type:q=q.where(Transaction.type==type)
    if start:q=q.where(Transaction.date>=start)
    if end:q=q.where(Transaction.date<=end)
    q=q.order_by(Transaction.amount if sort=="amount" else Transaction.date)
    return db.scalars(q).all()
@app.post("/transactions",response_model=TransactionOut,status_code=201)
def create_transaction(body:TransactionIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if body.type not in ["income","expense"]:raise HTTPException(422,"Type must be income or expense")
    data=body.model_dump()
    if data["category"]=="Other": data["category"]=categorize(data["merchant"]+" "+data["description"])["category"]
    t=Transaction(**data,user_id=user.id);db.add(t);db.commit();db.refresh(t);return t
def owned_transaction(tid,db,user):
    t=db.scalar(select(Transaction).where(Transaction.id==tid,Transaction.user_id==user.id))
    if not t:raise HTTPException(404,"Transaction not found")
    return t
@app.get("/transactions/{tid}",response_model=TransactionOut)
def get_transaction(tid:int,db:Session=Depends(get_db),user:User=Depends(current_user)):return owned_transaction(tid,db,user)
@app.put("/transactions/{tid}",response_model=TransactionOut)
def update_transaction(tid:int,body:TransactionIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if body.type not in ["income","expense"]:raise HTTPException(422,"Type must be income or expense")
    t=owned_transaction(tid,db,user)
    for k,v in body.model_dump().items():setattr(t,k,v)
    db.commit();db.refresh(t);return t
@app.delete("/transactions/{tid}",status_code=204)
def delete_transaction(tid:int,db:Session=Depends(get_db),user:User=Depends(current_user)):db.delete(owned_transaction(tid,db,user));db.commit()
@app.get("/budgets")
def list_budgets(db:Session=Depends(get_db),user:User=Depends(current_user)):
    items=db.scalars(select(Budget).where(Budget.user_id==user.id)).all();out=[]
    for b in items:
        month_start=date.fromisoformat(b.month+"-01")
        rows=db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.type=="expense",Transaction.date>=month_start,Transaction.date<date(month_start.year+(month_start.month==12),month_start.month%12+1,1))).all()
        spent=sum(t.amount for t in rows if b.category=="All categories" or t.category==b.category)
        out.append({"id":b.id,"user_id":b.user_id,"month":b.month,"category":b.category,"amount":b.amount,"spent":spent,"utilization":round(spent/b.amount*100,1)})
    return out
@app.post("/budgets",status_code=201)
def create_budget(body:BudgetIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    b=Budget(**body.model_dump(),user_id=user.id);db.add(b)
    try:db.commit()
    except Exception:db.rollback();raise HTTPException(409,"A budget for this month and category already exists")
    db.refresh(b);return b
def owned_budget(bid,db,user):
    b=db.scalar(select(Budget).where(Budget.id==bid,Budget.user_id==user.id))
    if not b:raise HTTPException(404,"Budget not found")
    return b
@app.put("/budgets/{bid}")
def update_budget(bid:int,body:BudgetIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    b=owned_budget(bid,db,user)
    for k,v in body.model_dump().items():setattr(b,k,v)
    db.commit();db.refresh(b);return b
@app.delete("/budgets/{bid}",status_code=204)
def delete_budget(bid:int,db:Session=Depends(get_db),user:User=Depends(current_user)):db.delete(owned_budget(bid,db,user));db.commit()
@app.get("/analytics/summary")
def summary(db:Session=Depends(get_db),user:User=Depends(current_user)):return monthly_summary(db,user.id)
@app.get("/analytics/categories")
def categories(db:Session=Depends(get_db),user:User=Depends(current_user)):return monthly_summary(db,user.id)["categories"]
@app.get("/analytics/monthly-trends")
def trends(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(Transaction).where(Transaction.user_id==user.id)).all();out={}
    for t in rows:
        key=t.date.strftime("%Y-%m");out.setdefault(key,{"month":key,"income":0,"expenses":0});out[key]["income" if t.type=="income" else "expenses"]+=t.amount
    return sorted(out.values(),key=lambda x:x["month"])[-6:]
@app.post("/ai/parse-transaction")
def parse(body:ParseRequest,user:User=Depends(current_user)):return parse_text(body.text)
@app.get("/ai/insights")
def get_insights(db:Session=Depends(get_db),user:User=Depends(current_user)):return insights(db,user.id)
@app.get("/ai/anomalies")
def anomalies(db:Session=Depends(get_db),user:User=Depends(current_user)):return [x for x in insights(db,user.id) if x["kind"]=="anomaly"]
@app.get("/ai/forecast")
def forecast(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.type=="expense")).all();sums={}
    for t in rows:
        k=t.date.strftime("%Y-%m");sums[k]=sums.get(k,0)+t.amount
    today=date.today();current_month=today.strftime("%Y-%m")
    completed=sorted((k,v) for k,v in sums.items() if k<current_month)
    history=[{"month":k,"actual":round(v,2)} for k,v in completed[-6:]]
    partial={"month":current_month,"actual":round(sums[current_month],2)} if current_month in sums else None
    next_month=date(today.year+(today.month==12),today.month%12+1,1).strftime("%Y-%m")
    if len(completed)<3:
        return {"available":False,"reason":"Add expenses in at least three completed months to get a reliable forecast.","completed_months":len(completed),"history":history,"partial_month":partial,"next_month":next_month}
    last_three=completed[-3:];values=[v for _,v in last_three];pred=sum(values)/3
    return {"available":True,"method":"3-month moving average using completed months","predicted":round(pred,2),"uncertainty":round(pstdev(values),2),"next_month":next_month,"history":history,"partial_month":partial}
def _pdf_preview(content: bytes, db: Session, user: User):
    try:
        parsed = parse_statement_pdf(content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    existing = db.scalars(select(Transaction).where(Transaction.user_id == user.id)).all()
    descriptions = [tx.description or "" for tx in existing]
    existing_refs = set()
    existing_external = set()
    for description in descriptions:
        ref_match = re.search(r"PDF import ref:\s*([A-Za-z0-9:_-]+)", description)
        if ref_match: existing_refs.add(ref_match.group(1))
        legacy_match = re.search(r"Txn ID:\s*([^|\s]+)", description)
        if legacy_match: existing_external.add(legacy_match.group(1))
    rows = parsed["transactions"]
    for row in rows:
        row["duplicate"] = row["source_ref"] in existing_refs or bool(row["external_ref"] and row["external_ref"] in existing_external)
    parsed["summary"]["duplicates"] = sum(row["duplicate"] for row in rows)
    parsed["summary"]["new_count"] = len(rows) - parsed["summary"]["duplicates"]
    parsed["warnings"] = ["Categories are suggestions; review them before import.", "Scanned image-only PDFs are not supported yet."]
    return parsed

@app.post("/transactions/import-pdf/preview")
async def preview_statement_pdf(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    content = await file.read(12 * 1024 * 1024 + 1)
    return _pdf_preview(content, db, user)

@app.post("/transactions/import-pdf/commit")
def commit_statement_pdf(body: PdfImportCommit, db: Session = Depends(get_db), user: User = Depends(current_user)):
    existing = db.scalars(select(Transaction).where(Transaction.user_id == user.id)).all()
    existing_descriptions = [tx.description or "" for tx in existing]
    source_refs = set()
    external_refs = set()
    for description in existing_descriptions:
        ref_match = re.search(r"PDF import ref:\s*([A-Za-z0-9:_-]+)", description)
        if ref_match: source_refs.add(ref_match.group(1))
        legacy_match = re.search(r"Txn ID:\s*([^|\s]+)", description)
        if legacy_match: external_refs.add(legacy_match.group(1))
    inserted = 0
    skipped = 0
    for row in body.transactions:
        if row.source_ref in source_refs or (row.external_ref and row.external_ref in external_refs):
            skipped += 1
            continue
        detail = f"PDF statement import | PDF import ref: {row.source_ref}"
        if row.external_ref:
            detail += f" | Txn ID: {row.external_ref}"
        if row.description:
            detail += f" | {row.description}"
        db.add(Transaction(
            user_id=user.id, date=row.date, amount=row.amount, type=row.type,
            category=row.category, merchant=row.merchant, description=detail[:500],
            payment_method=row.payment_method,
        ))
        source_refs.add(row.source_ref)
        if row.external_ref: external_refs.add(row.external_ref)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "skipped_duplicates": skipped}
