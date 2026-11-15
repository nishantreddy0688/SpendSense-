from datetime import datetime, date, timezone
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transaction_user_date", "user_id", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, default=date.today)
    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(80), default="Other")
    merchant: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(String(500), default="")
    payment_method: Mapped[str] = mapped_column(String(40), default="UPI")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="transactions")

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (Index("ix_budget_user_month_category", "user_id", "month", "category", unique=True),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(7))
    category: Mapped[str] = mapped_column(String(80), default="All categories")
    amount: Mapped[float] = mapped_column(Float)
    user = relationship("User", back_populates="budgets")

class Insight(Base):
    __tablename__ = "insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    detail: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(30), default="insight")
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(9), default="#218452")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
