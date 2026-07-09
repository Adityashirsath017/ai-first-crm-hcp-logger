import sys
import os

# Add the backend directory to path so app can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base, SessionLocal
from app.models import HCP, ProductCatalog

def seed_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed HCPs if none exist
        if db.query(HCP).count() == 0:
            print("Seeding Healthcare Professionals (HCPs)...")
            hcps = [
                HCP(name="Dr. Ramesh Sharma", specialty="Oncology", hospital="Metro Cancer Institute", email="ramesh.sharma@metro.com"),
                HCP(name="Dr. Sarah Connor", specialty="Cardiology", hospital="Heart Care Center", email="s.connor@heartcare.org"),
                HCP(name="Dr. Amit Patel", specialty="Endocrinology", hospital="Apex Diabetes Clinic", email="amit.patel@apex.in"),
                HCP(name="Dr. Jane Smith", specialty="Oncology", hospital="City Medical Center", email="jane.smith@citymed.org"),
                HCP(name="Dr. Priya Nair", specialty="Neurology", hospital="Narayana Health", email="priya.nair@narayana.com"),
                HCP(name="Dr. David Miller", specialty="Cardiology", hospital="St. Jude Hospital", email="d.miller@stjude.org"),
            ]
            db.add_all(hcps)
            db.commit()
            print(f"Successfully seeded {len(hcps)} HCPs.")
        else:
            print("HCPs already seeded.")

        # 2. Seed Materials and Samples if none exist
        if db.query(ProductCatalog).count() == 0:
            print("Seeding Product Catalog (Materials and Samples)...")
            items = [
                # Materials (Brochures, PDFs)
                ProductCatalog(name="OncoBoost Phase III PDF", category="material", description="Detailed efficacy and safety results for OncoBoost Phase III trial."),
                ProductCatalog(name="CardioLife Product Monograph", category="material", description="Full prescribing information and pharmacology for CardioLife."),
                ProductCatalog(name="GlucoShield Patient Brochure", category="material", description="Patient education brochure for diabetes management with GlucoShield."),
                ProductCatalog(name="OncoBoost Efficacy Infographic", category="material", description="One-page infographic summarizing clinical endpoints."),
                ProductCatalog(name="CardioLife Safety Trial Results", category="material", description="Cardiovascular outcomes study publication reprint."),
                
                # Samples
                ProductCatalog(name="OncoBoost 10mg Starter Pack", category="sample", description="10mg capsules (10-day supply) for patient initiation."),
                ProductCatalog(name="OncoBoost 25mg Capsules", category="sample", description="25mg maintenance dose sample pack (7-day supply)."),
                ProductCatalog(name="CardioLife 20mg Sample Kit", category="sample", description="20mg once-daily tablets sample pack (14-day supply)."),
                ProductCatalog(name="GlucoShield 5mg Vials", category="sample", description="5mg injectable solution sample vials."),
                ProductCatalog(name="GlucoShield 10mg Tablets", category="sample", description="10mg oral tablets sample pack.")
            ]
            db.add_all(items)
            db.commit()
            print(f"Successfully seeded {len(items)} catalog items.")
        else:
            print("Product catalog already seeded.")
            
    except Exception as e:
        print(f"An error occurred during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
