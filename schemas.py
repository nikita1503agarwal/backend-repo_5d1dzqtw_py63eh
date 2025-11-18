"""
Database Schemas for Insurance Portal

Each Pydantic model represents a MongoDB collection. Collection name is the
lowercase of the class name (e.g., Policy -> "policy").
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date, datetime

# Core domain models
class Policy(BaseModel):
    policy_number: str = Field(..., description="Unique policy number")
    product: str = Field(..., description="Product name, e.g., Commercial Property")
    status: Literal["active", "expired", "cancelled"] = "active"
    start_date: date
    end_date: date
    premium: float = Field(..., ge=0)
    insured_entity: str

class DocumentItem(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, description="e.g., Policy, Invoice, Evidence")
    policy_number: Optional[str] = None

class Invoice(BaseModel):
    invoice_number: str
    amount: float = Field(..., ge=0)
    due_date: date
    status: Literal["outstanding", "paid"] = "outstanding"
    policy_number: Optional[str] = None

class Renewal(BaseModel):
    policy_number: str
    product: str
    renewal_date: date
    status: Literal["due", "submitted", "not_required"] = "due"

class Activity(BaseModel):
    type: str = Field(..., description="Action type, e.g., policy_renewal, payment_made, document_uploaded")
    message: str
    actor: Optional[str] = "system"
    occurred_at: Optional[datetime] = None

class Notification(BaseModel):
    title: str
    message: str
    level: Literal["info", "warning", "critical"] = "info"

class Update(BaseModel):
    title: str
    label: Optional[str] = "Latest Update"
    description: Optional[str] = None
    date_str: str

class TeamMember(BaseModel):
    name: str
    role: str
    email: EmailStr
    phone: str
    linkedin: Optional[str] = None
