import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, HCP, Material, Sample, Interaction, FollowUpTask

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm.db")

# For SQLite, we need connect_args={"check_same_thread": False}
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

def seed_database(db):
    # Check if we already have HCPs seeded
    if db.query(HCP).first() is not None:
        return
        
    print("Seeding database with mock data...")
    
    # 1. Seed HCPs
    hcps = [
        HCP(name="Dr. Sarah Patel", specialty="Oncologist", clinic="Patel Oncology Center", email="sarah.patel@pateloncology.com", phone="555-0192"),
        HCP(name="Dr. Robert Chen", specialty="Cardiologist", clinic="Metro Heart Center", email="r.chen@metroheart.org", phone="555-0143"),
        HCP(name="Dr. Amanda Ross", specialty="Neurologist", clinic="Neurological Care Associates", email="amanda.ross@neurocare.com", phone="555-0188"),
        HCP(name="Dr. Jane Smith", specialty="Pediatrician", clinic="Children's Health Group", email="jsmith@childhealth.org", phone="555-0111")
    ]
    for h in hcps:
        db.add(h)
    db.commit()
    
    # 2. Seed Materials
    materials = [
        Material(name="OncoBoost Phase III PDF", type="PDF", description="Phase III clinical trial results for OncoBoost in lung cancer patients."),
        Material(name="CardioShield Brochure", type="Brochure", description="Patient education brochure explaining dosage and side effects of CardioShield."),
        Material(name="NeuroMax Efficacy Study", type="Study", description="Double-blind efficacy study details of NeuroMax vs placebo."),
        Material(name="Immunex Patient Guide", type="Brochure", description="Step-by-step user guide for self-administering Immunex.")
    ]
    for m in materials:
        db.add(m)
    db.commit()
    
    # 3. Seed Samples
    samples = [
        Sample(name="OncoBoost Starter Packs", stock_quantity=25, description="Starter kit containing 7 daily doses of OncoBoost."),
        Sample(name="CardioShield Daily Dose", stock_quantity=50, description="Sample pack with 10 tablets of CardioShield."),
        Sample(name="NeuroMax 10mg Tablets", stock_quantity=15, description="Neurology starter sample pack for NeuroMax 10mg."),
        Sample(name="Immunex Injection Kits", stock_quantity=10, description="Single-use pre-filled syringe sample kit for Immunex.")
    ]
    for s in samples:
        db.add(s)
    db.commit()
    
    # Refresh HCP object references to log past interactions
    hcp_patel = db.query(HCP).filter(HCP.name == "Dr. Sarah Patel").first()
    hcp_chen = db.query(HCP).filter(HCP.name == "Dr. Robert Chen").first()
    
    material_ob = db.query(Material).filter(Material.name == "OncoBoost Phase III PDF").first()
    sample_ob = db.query(Sample).filter(Sample.name == "OncoBoost Starter Packs").first()
    
    # 4. Seed Past Interactions
    interaction1 = Interaction(
        hcp_id=hcp_patel.id,
        type="Call",
        date="2026-06-15",
        time="10:30",
        attendees="Dr. Sarah Patel, Sales Rep Alex",
        topics_discussed="Introduction to OncoBoost. Discussed mechanism of action and efficacy rates.",
        sentiment="Positive",
        outcomes="Dr. Patel requested clinical trial literature. Expressed interest in prescribing it to lung cancer patients.",
        follow_up_actions="Send OncoBoost Phase III PDF and schedule an in-person follow-up in July."
    )
    # Associate material with interaction
    interaction1.materials.append(material_ob)
    db.add(interaction1)
    
    interaction2 = Interaction(
        hcp_id=hcp_chen.id,
        type="Meeting",
        date="2026-06-20",
        time="14:00",
        attendees="Dr. Robert Chen, Sales Rep Alex",
        topics_discussed="CardioShield safety profile. Addressed concerns about medication interactions with beta blockers.",
        sentiment="Neutral",
        outcomes="Dr. Chen was cautious but open to reading more safety reports. Did not request samples yet.",
        follow_up_actions="Follow up via email in 2-3 weeks with updated safety reports."
    )
    db.add(interaction2)
    db.commit()
    
    # 5. Seed Follow Up Tasks
    task1 = FollowUpTask(
        hcp_id=hcp_patel.id,
        interaction_id=interaction1.id,
        description="Schedule follow-up meeting to discuss Phase III results.",
        due_date="2026-07-20",
        status="Pending"
    )
    db.add(task1)
    db.commit()
    
    print("Database seeding completed.")
