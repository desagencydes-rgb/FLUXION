"""
FLUXION JWT Authentication Module.

Provides:
  - Password hashing (bcrypt via passlib)
  - JWT token creation / verification (python-jose)
  - FastAPI dependency: get_current_user
  - Auth router with /auth/login and /auth/register endpoints
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from commun.database import async_session, User

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "dev")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# ── Password Hashing ────────────────────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


# ── JWT Token ────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT with the given payload."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and verify a JWT. Returns the payload dict."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ── FastAPI Security Scheme ──────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency that extracts the current user from:
    1. Bearer JWT token (production)
    2. X-User-Role header (dev fallback when JWT_SECRET="dev")

    Returns dict with keys: user_id, role, org_id
    """
    # Try JWT first
    if credentials and credentials.credentials:
        payload = verify_token(credentials.credentials)
        return {
            "user_id": payload["sub"],
            "role": payload.get("role", "driver"),
            "org_id": payload.get("org_id"),
        }

    # Dev-mode fallback: X-User-Role header
    if JWT_SECRET == "dev":
        role = request.headers.get("X-User-Role", "").lower().strip()
        if role:
            return {"user_id": "dev", "role": role, "org_id": None}

    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Provide a Bearer token or X-User-Role header (dev mode).",
    )


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    org_id: Optional[int] = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "driver"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_id: int


# ── Auth Router ──────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """Authenticate with email + password, receive a JWT token."""
    async with async_session() as session:
        stmt = select(User).where(User.email == payload.email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "org_id": user.organization_id,
    })

    return LoginResponse(
        access_token=token,
        role=user.role,
        org_id=user.organization_id,
    )


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new user. Only super_admin can register new users.
    """
    if current_user["role"] != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can register new users",
        )

    if payload.role not in ("driver", "fleet_manager", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {payload.role}",
        )

    async with async_session() as session:
        # Check duplicate email
        existing = await session.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{payload.email}' already registered",
            )

        new_user = User(
            organization_id=payload.organization_id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        session.add(new_user)
        await session.commit()

    return {"detail": f"User '{payload.email}' created with role '{payload.role}'"}
