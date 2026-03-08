"""
FLUXION — Multi-Tenancy Query Helpers
Provides async SQLAlchemy queries automatically filtered by organization_id.
"""
from typing import List, Optional
from sqlalchemy import select, desc
from datetime import date, timedelta

from commun.database import (
    async_session,
    User,
    CamionDB,
    PointCollecteDB,
    SavingsLog
)

async def get_user_by_email(email: str) -> Optional[User]:
    """Retrieve a user by email, across all orgs (email is unique)."""
    async with async_session() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def get_trucks(org_id: int) -> List[CamionDB]:
    """Retrieve all active trucks for a specific organization."""
    async with async_session() as session:
        stmt = select(CamionDB).where(
            CamionDB.organization_id == org_id,
            CamionDB.is_active == True
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def get_collection_points(org_id: int) -> List[PointCollecteDB]:
    """Retrieve all active collection points for a specific organization."""
    async with async_session() as session:
        stmt = select(PointCollecteDB).where(
            PointCollecteDB.organization_id == org_id,
            PointCollecteDB.is_active == True
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def get_savings_history(org_id: int, days: int = 30) -> List[SavingsLog]:
    """Retrieve the last N days of savings logs for an organization."""
    cutoff_date = date.today() - timedelta(days=days)
    async with async_session() as session:
        stmt = select(SavingsLog).where(
            SavingsLog.organization_id == org_id,
            SavingsLog.log_date >= cutoff_date
        ).order_by(SavingsLog.log_date.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def create_savings_log(org_id: int, data: dict) -> SavingsLog:
    """Create a new savings log entry for an organization."""
    async with async_session() as session:
        try:
            log = SavingsLog(
                organization_id=org_id,
                log_date=data.get('log_date', date.today()),
                distance_naive_km=data['distance_naive_km'],
                distance_optimized_km=data['distance_optimized_km'],
                money_saved=data['money_saved'],
                co2_reduced_kg=data['co2_reduced_kg'],
                fuel_saved_l=data['fuel_saved_l']
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log
        except Exception:
            await session.rollback()
            raise
