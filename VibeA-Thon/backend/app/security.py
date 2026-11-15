from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import get_db
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth = OAuth2PasswordBearer(tokenUrl="/auth/login")
def hash_password(value): return pwd.hash(value)
def verify_password(value, hashed): return pwd.verify(value, hashed)
def make_token(user_id): return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_minutes)}, settings.secret_key, algorithm="HS256")
def current_user(token: str = Depends(oauth), db: Session = Depends(get_db)):
    try: user_id = int(jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"])
    except (JWTError, KeyError, ValueError): raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate":"Bearer"})
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, "Account not found")
    return user
