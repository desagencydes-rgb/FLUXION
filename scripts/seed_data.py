"""
FLUXION — Data Seeding Script (Idempotent)
Populates the async PostgreSQL database with realistic demo data for Casablanca.
"""
import os
import sys
import asyncio
import random
from datetime import date, timedelta
from dotenv import load_dotenv

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from commun.database import (
    Organization, User, CamionDB, PointCollecteDB, SavingsLog
)
from live_bridge.auth import hash_password

# Ensure we can import from commun and live_bridge
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

# Casablanca center coordinates
CASA_LAT = 33.5731
CASA_LON = -7.5898

def jitter(coord: float, spread: float = 0.05) -> float:
    """Adds small random noise to coordinates."""
    return coord + random.uniform(-spread, spread)

async def seed_data():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # 1. Organization
        stmt = select(Organization).where(Organization.name == "Ville de Casablanca")
        result = await session.execute(stmt)
        org = result.scalar_one_or_none()

        if not org:
            print("Seeding Organization...")
            org = Organization(name="Ville de Casablanca")
            session.add(org)
            await session.commit()
        else:
            print("Organization exists.")

        # 2. Users
        users_to_create = [
            ("super@ville.ma", "admin123", "super_admin", "Admin", "Super"),
            ("manager@ville.ma", "manager123", "fleet_manager", "Fleet", "Manager"),
            ("driver@ville.ma", "driver123", "driver", "Ali", "Chauffeur")
        ]

        for email, pwd, role, fname, lname in users_to_create:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                print(f"Seeding User: {email}")
                u = User(
                    organization_id=org.id,
                    email=email,
                    password_hash=hash_password(pwd),
                    role=role,
                    first_name=fname,
                    last_name=lname
                )
                session.add(u)
        await session.commit()

        # 3. Trucks
        plates = ["12345-A-1", "67890-B-6", "11223-D-5", "44556-H-2", "99887-a-8"]
        for idx, plate in enumerate(plates):
            stmt = select(CamionDB).where(CamionDB.plate_number == plate)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                print(f"Seeding Truck: {plate}")
                cap = random.choice([3000, 4000, 4500, 5000, 6000])
                c = CamionDB(
                    organization_id=org.id,
                    plate_number=plate,
                    capacite=float(cap),
                    cout_fixe=float(random.randint(100, 300))
                )
                session.add(c)
        await session.commit()

        # 4. Collection Points
        stmt = select(PointCollecteDB).where(PointCollecteDB.organization_id == org.id)
        res = await session.execute(stmt)
        existing_pts_count = len(res.scalars().all())

        if existing_pts_count < 20:
            print("Seeding Collection Points...")
            types = ["waste_basket", "recycling", "restaurant", "pharmacy", "hotel", "supermarket"]
            for i in range(20 - existing_pts_count):
                pt_type = random.choice(types)
                lat = jitter(CASA_LAT)
                lon = jitter(CASA_LON)
                vol = random.uniform(50, 500)
                p = PointCollecteDB(
                    organization_id=org.id,
                    external_id=f"sim_{i}",
                    nom=f"Point {pt_type.title()} {i+1}",
                    type=pt_type,
                    lat=lat,
                    lon=lon,
                    volume_estime=vol
                )
                session.add(p)
            await session.commit()
        else:
            print("Collection Points exist.")

        # 5. Savings Logs (7 days)
        stmt = select(SavingsLog).where(SavingsLog.organization_id == org.id)
        res = await session.execute(stmt)
        if not res.scalars().first():
            print("Seeding Savings Logs...")
            today = date.today()
            for i in range(7):
                log_date = today - timedelta(days=(6 - i))
                naive = random.uniform(100, 150)
                opt = naive * random.uniform(0.6, 0.8) # 20% to 40% savings
                dist_saved = naive - opt
                fuel = dist_saved * 0.35 # CONSOMMATION_L_PAR_KM aprox
                co2 = fuel * 2.68
                money = fuel * 1.85

                s = SavingsLog(
                    organization_id=org.id,
                    log_date=log_date,
                    distance_naive_km=naive,
                    distance_optimized_km=opt,
                    money_saved=money,
                    co2_reduced_kg=co2,
                    fuel_saved_l=fuel
                )
                session.add(s)
            await session.commit()
        else:
            print("Savings Logs exist.")

    print("✅ Seeding complete!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())
