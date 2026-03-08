"""
FLUXION Database Module — Async PostgreSQL with SQLite fallback.

Uses SQLAlchemy 2.0 async engine + ORM models matching commun/schema.sql.
If DATABASE_URL is not set, falls back to SQLite for local development.
"""
import os
import json
import enum
from datetime import datetime, date
from typing import Optional, List
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy import (
    String, Boolean, Text, Integer, Float, Date, Enum,
    ForeignKey, Index, func, select, desc
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Build engine: PostgreSQL (asyncpg) or SQLite (aiosqlite)
if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
else:
    # Fallback: async SQLite
    _db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data.db"
    )
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{_db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    fleet_manager = "fleet_manager"
    driver = "driver"


class PointType(str, enum.Enum):
    waste_basket = "waste_basket"
    recycling = "recycling"
    fuel = "fuel"
    restaurant = "restaurant"
    pharmacy = "pharmacy"
    hotel = "hotel"
    supermarket = "supermarket"
    depot = "depot"


# ── Base ─────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── ORM Models (matching schema.sql) ────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    camions: Mapped[List["CamionDB"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    points: Mapped[List["PointCollecteDB"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    savings_logs: Mapped[List["SavingsLog"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="driver")
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="users")


class CamionDB(Base):
    __tablename__ = "camions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(50), nullable=False)
    capacite: Mapped[float] = mapped_column(Float, nullable=False)
    cout_fixe: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="camions")


class PointCollecteDB(Base):
    __tablename__ = "points_collecte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(100))
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    override_lat: Mapped[Optional[float]] = mapped_column(Float)
    override_lon: Mapped[Optional[float]] = mapped_column(Float)
    volume_estime: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="points")

    __table_args__ = (
        Index("idx_points_org", "organization_id"),
    )


class SavingsLog(Base):
    __tablename__ = "savings_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, default=func.current_date())
    distance_naive_km: Mapped[float] = mapped_column(Float, nullable=False)
    distance_optimized_km: Mapped[float] = mapped_column(Float, nullable=False)
    money_saved: Mapped[float] = mapped_column(Float, nullable=False)
    co2_reduced_kg: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_saved_l: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="savings_logs")

    __table_args__ = (
        Index("idx_savings_org_date", "organization_id", "log_date"),
    )


# ── Event Log (kept for backward compat with simulation) ────────────────────

class EventLog(Base):
    __tablename__ = "evenements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=func.now())
    type: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)


class EtatZone(Base):
    __tablename__ = "etats_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=func.now())
    zone_id: Mapped[int] = mapped_column(Integer, nullable=False)
    niveau_remplissage: Mapped[float] = mapped_column(Float, nullable=False)


# ── Database Initialization ─────────────────────────────────────────────────

async def init_db():
    """Creates all tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Session Context Manager ─────────────────────────────────────────────────

@asynccontextmanager
async def get_session():
    """Yields an async session, rolls back on error."""
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ── Legacy-Compatible Functions (async) ──────────────────────────────────────

async def sauvegarder_evenement(type_evt: str, data: dict):
    """Saves an event to the database."""
    async with get_session() as session:
        event = EventLog(type=type_evt, data=json.dumps(data, ensure_ascii=False))
        session.add(event)


async def sauvegarder_etat_zone(zone_id: int, niveau: float):
    """Saves zone fill-level state."""
    async with get_session() as session:
        etat = EtatZone(zone_id=zone_id, niveau_remplissage=niveau)
        session.add(etat)


async def charger_derniers_evenements(limite: int = 50) -> list:
    """Loads the N most recent events."""
    async with get_session() as session:
        stmt = select(EventLog).order_by(desc(EventLog.id)).limit(limite)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "timestamp": str(r.timestamp),
                "type": r.type,
                "data": json.loads(r.data),
            }
            for r in rows
        ]


# ── Synchronous Fallback (for non-async callers) ────────────────────────────
# Keeps backward compatibility with existing sync code that calls these.

import sqlite3

_SYNC_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.db"
)


def _get_sync_connection():
    """Returns a SQLite connection for sync callers, creates tables if needed."""
    conn = sqlite3.connect(_SYNC_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evenements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            type TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS etats_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            zone_id INTEGER NOT NULL,
            niveau_remplissage REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def sauvegarder_evenement_sync(type_evt: str, data: dict):
    """Synchronous event saver (legacy compatibility)."""
    conn = _get_sync_connection()
    conn.execute("INSERT INTO evenements (type, data) VALUES (?, ?)",
                 (type_evt, json.dumps(data, ensure_ascii=False)))
    conn.commit()
    conn.close()


def sauvegarder_etat_zone_sync(zone_id: int, niveau: float):
    """Synchronous zone state saver (legacy compatibility)."""
    conn = _get_sync_connection()
    conn.execute("INSERT INTO etats_zones (zone_id, niveau_remplissage) VALUES (?, ?)",
                 (zone_id, niveau))
    conn.commit()
    conn.close()


def charger_derniers_evenements_sync(limite: int = 50) -> list:
    """Synchronous event loader (legacy compatibility)."""
    conn = _get_sync_connection()
    cursor = conn.execute(
        "SELECT timestamp, type, data FROM evenements ORDER BY id DESC LIMIT ?", (limite,))
    result = [{"timestamp": r[0], "type": r[1], "data": json.loads(r[2])} for r in cursor]
    conn.close()
    return result
