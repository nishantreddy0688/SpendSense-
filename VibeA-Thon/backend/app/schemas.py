from datetime import date as DateType
from typing import Literal
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class Register(BaseModel): name: str = Field(min_length=1, max_length=100); email: EmailStr; password: str = Field(min_length=8)
class Login(BaseModel): email: EmailStr; password: str
class UserOut(BaseModel): id: int; name: str; email: EmailStr; model_config = ConfigDict(from_attributes=True)
class Token(BaseModel): access_token: str; token_type: str = "bearer"; user: UserOut
class TransactionIn(BaseModel): date: DateType = Field(default_factory=DateType.today); amount: float = Field(gt=0); type: str; category: str = "Other"; merchant: str = ""; description: str = ""; payment_method: str = "UPI"
class TransactionOut(TransactionIn): id: int; user_id: int; model_config = ConfigDict(from_attributes=True)
class BudgetIn(BaseModel): month: str = Field(pattern=r"^\d{4}-\d{2}$"); category: str = "All categories"; amount: float = Field(gt=0)
class BudgetOut(BudgetIn): id: int; user_id: int; spent: float = 0; model_config = ConfigDict(from_attributes=True)
class ParseRequest(BaseModel): text: str = Field(min_length=3, max_length=500)
class PdfTransactionIn(BaseModel):
    date: DateType
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    category: str = Field(min_length=1, max_length=80)
    merchant: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    payment_method: str = Field(default="Other", max_length=40)
    source_ref: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")
    external_ref: str | None = Field(default=None, max_length=180)
class PdfImportCommit(BaseModel):
    transactions: list[PdfTransactionIn] = Field(min_length=1, max_length=1000)
