"""
Seed a demo broker user into the database and verify authentication.
"""
from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal
from app.models.broker import Broker
from app.core.security import hash_password, verify_password

db = SessionLocal()

try:
    email = "admin@reality.ai"
    password = "adminpassword123"

    # Delete existing broker if present to avoid duplicate error
    existing = db.query(Broker).filter(Broker.email == email).first()
    if existing:
        db.delete(existing)
        db.commit()

    # Create new broker account
    broker = Broker(
        name="Admin Broker",
        email=email,
        password_hash=hash_password(password)
    )
    db.add(broker)
    db.commit()
    db.refresh(broker)

    print(f"✅ Demo Broker Created:")
    print(f"   ID: {broker.id}")
    print(f"   Email: {broker.email}")
    print(f"   Password: {password}")
    print(f"   Password Hash Verified: {verify_password(password, broker.password_hash)}")

finally:
    db.close()
