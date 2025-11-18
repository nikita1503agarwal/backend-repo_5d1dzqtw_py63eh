import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from database import db, create_document, get_documents
from schemas import Policy, DocumentItem, Invoice, Renewal, Activity, Notification, Update, TeamMember

app = FastAPI(title="Insurance Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Insurance Portal Backend Running"}

# Seed some demo data if collections are empty
@app.on_event("startup")
async def seed_demo():
    try:
        # Policies
        if db and db["policy"].count_documents({}) == 0:
            create_document("policy", Policy(policy_number="CP-12345", product="Commercial Property", start_date=datetime(2024,1,1), end_date=datetime(2024,12,31), premium=12000, insured_entity="Acme Corp", status="active"))
            create_document("policy", Policy(policy_number="GL-67890", product="General Liability", start_date=datetime(2024,3,1), end_date=datetime(2025,2,28), premium=8500, insured_entity="Acme Corp", status="active"))
            create_document("policy", Policy(policy_number="CY-22222", product="Cyber", start_date=datetime(2024,6,1), end_date=datetime(2025,5,31), premium=4000, insured_entity="Acme Corp", status="active"))
        # Invoices
        if db and db["invoice"].count_documents({}) == 0:
            create_document("invoice", Invoice(invoice_number="INV-001", amount=15000, due_date=datetime(2025,11,15), status="outstanding"))
            create_document("invoice", Invoice(invoice_number="INV-002", amount=9500, due_date=datetime(2025,11,20), status="outstanding"))
        # Renewals
        if db and db["renewal"].count_documents({}) == 0:
            create_document("renewal", Renewal(policy_number="XX-0000", product="Directors & Officers", renewal_date=datetime(2026,2,1), status="not_required"))
        # Risk Updates pending
        if db and db["update"].count_documents({}) == 0:
            create_document("update", Update(title="New Cyber Insurance Requirements for 2025", description="Multi-factor authentication and endpoint detection are now standard.", date_str="Nov 10, 2024"))
        # Team members
        if db and db["teammember"].count_documents({}) == 0:
            create_document("teammember", TeamMember(name="Monique Reibelt", role="Senior Broker", email="monique@example.com", phone="+1 (555) 123-4567", linkedin="https://linkedin.com/in/moniquereibelt"))
            create_document("teammember", TeamMember(name="Stuart Madden", role="Service Agent", email="stuart@example.com", phone="+1 (555) 987-6543", linkedin="https://linkedin.com/in/stuartmadden"))
        # Activities
        if db and db["activity"].count_documents({}) == 0:
            create_document("activity", Activity(type="policy_renewal", message="Commercial Property Insurance renewed for another year", actor="system", occurred_at=datetime.utcnow()))
            create_document("activity", Activity(type="payment_made", message="Payment of $10,000 recorded", actor="John Smith", occurred_at=datetime.utcnow() - timedelta(hours=6)))
            create_document("activity", Activity(type="document_uploaded", message="Evidence.pdf uploaded", actor="John Smith", occurred_at=datetime.utcnow() - timedelta(days=1)))
    except Exception:
        pass

# Notification bar endpoint
@app.get("/api/notification", response_model=Notification)
def get_notification():
    return Notification(
        title="Outstanding Invoices",
        message="Outstanding Invoices: $24,500 – Payment due Nov 15 & Nov 20",
        level="warning",
    )

# Dashboard counts
class DashboardCounts(BaseModel):
    active_policies: int
    outstanding_invoices: int
    outstanding_total: float
    renewals_due: int
    risk_updates: int

@app.get("/api/dashboard", response_model=DashboardCounts)
def get_dashboard_counts():
    active = db["policy"].count_documents({"status": "active"}) if db else 3
    outstanding = list(db["invoice"].find({"status": "outstanding"})) if db else []
    outstanding_count = len(outstanding) if outstanding else 2
    outstanding_total = sum([i.get("amount", 0) for i in outstanding]) if outstanding else 24500
    renewals_due = db["renewal"].count_documents({"status": "due"}) if db else 0
    risk_updates = db["update"].count_documents({}) if db else 1
    return DashboardCounts(
        active_policies=active,
        outstanding_invoices=outstanding_count,
        outstanding_total=outstanding_total,
        renewals_due=renewals_due,
        risk_updates=risk_updates,
    )

# Policies list
@app.get("/api/policies", response_model=List[Policy])
def list_policies():
    docs = get_documents("policy") if db else []
    # Convert Mongo _id and timestamps
    res: List[Policy] = []
    for d in docs:
        d.pop("_id", None)
        # Convert dates if stored as datetime
        for k in ["start_date", "end_date"]:
            if isinstance(d.get(k), datetime):
                d[k] = d[k].date()
        res.append(Policy(**d))
    return res

# Documents upload and list
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), policy_number: Optional[str] = Form(None)):
    # In a real app you'd store the file in S3 or similar.
    item = DocumentItem(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=None,
        category="Uploaded",
        policy_number=policy_number,
    )
    if db:
        create_document("documentitem", item)
    return {"status": "ok", "filename": file.filename}

@app.get("/api/documents", response_model=List[DocumentItem])
async def list_documents():
    docs = get_documents("documentitem") if db else []
    res: List[DocumentItem] = []
    for d in docs:
        d.pop("_id", None)
        res.append(DocumentItem(**d))
    return res

# Invoices endpoints
@app.get("/api/invoices", response_model=List[Invoice])
def list_invoices():
    docs = get_documents("invoice") if db else []
    for d in docs:
        d.pop("_id", None)
        if isinstance(d.get("due_date"), datetime):
            d["due_date"] = d["due_date"].date()
    return [Invoice(**d) for d in docs]

# Renewals endpoints
@app.get("/api/renewals", response_model=List[Renewal])
def list_renewals():
    docs = get_documents("renewal") if db else []
    for d in docs:
        d.pop("_id", None)
        if isinstance(d.get("renewal_date"), datetime):
            d["renewal_date"] = d["renewal_date"].date()
    return [Renewal(**d) for d in docs]

# Insurance updates/news
@app.get("/api/updates", response_model=List[Update])
def list_updates():
    docs = get_documents("update") if db else []
    for d in docs:
        d.pop("_id", None)
    if not docs:
        docs = [Update(title="New Cyber Insurance Requirements for 2025", description="Multi-factor authentication and endpoint detection are now standard.", date_str="Nov 10, 2024").model_dump()]
    return [Update(**d) for d in docs]

# Team members
@app.get("/api/team", response_model=List[TeamMember])
def list_team():
    docs = get_documents("teammember") if db else []
    for d in docs:
        d.pop("_id", None)
    if not docs:
        docs = [
            TeamMember(name="Monique Reibelt", role="Senior Broker", email="monique@example.com", phone="+1 (555) 123-4567", linkedin="https://linkedin.com/in/moniquereibelt").model_dump(),
            TeamMember(name="Stuart Madden", role="Service Agent", email="stuart@example.com", phone="+1 (555) 987-6543", linkedin="https://linkedin.com/in/stuartmadden").model_dump(),
        ]
    return [TeamMember(**d) for d in docs]

# Activity feed
@app.get("/api/activities", response_model=List[Activity])
def list_activities():
    docs = get_documents("activity") if db else []
    for d in docs:
        d.pop("_id", None)
        if isinstance(d.get("occurred_at"), datetime):
            d["occurred_at"] = d["occurred_at"].isoformat()
    if not docs:
        docs = [
            Activity(type="policy_renewal", message="Commercial Property Insurance renewed for another year", actor="system", occurred_at=datetime.utcnow()).model_dump(),
            Activity(type="payment_made", message="Payment made", actor="John Smith", occurred_at=datetime.utcnow()).model_dump(),
            Activity(type="document_uploaded", message="Document uploaded", actor="John Smith", occurred_at=datetime.utcnow()).model_dump(),
        ]
    return [Activity(**d) for d in docs]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
