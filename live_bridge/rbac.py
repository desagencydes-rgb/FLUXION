"""
Role-Based Access Control (RBAC) middleware for FLUXION.

Roles:
  - super_admin: Full access to all endpoints.
  - fleet_manager: Dashboard, NSGA-II weight sliders, config, event triggers.
  - driver: Read-only state, GPS heartbeat, collection checklist.

Authentication order:
  1. Bearer JWT token (production) → extracts role from token payload
  2. X-User-Role header (dev fallback, only when JWT_SECRET="dev")
"""
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "dev")

# Role hierarchy (higher index = more permissions)
ROLES = ["driver", "fleet_manager", "super_admin"]

# Endpoint access control matrix
# Maps path prefixes to the minimum role required
ENDPOINT_PERMISSIONS: Dict[str, Optional[str]] = {
    # Fleet Manager+ only
    "/api/simulation/weights":  "fleet_manager",
    "/api/config":              "fleet_manager",
    "/api/events/trigger":      "fleet_manager",
    "/live/ingest-network":     "fleet_manager",
    "/live/waste-baskets":      "fleet_manager",
    "/live/pois":               "fleet_manager",

    # Driver+ (most read endpoints)
    "/api/state":               "driver",
    "/api/savings":             "driver",
    "/api/simulation/step":     "driver",
    "/api/simulation/play":     "driver",
    "/api/simulation/pause":    "driver",
    "/live/gps-snap":           "driver",
    "/live/health":             "driver",

    # WebSocket — open
    "/ws/":                     "driver",

    # Auth — open to all (no auth required)
    "/auth/login":              None,
    "/auth/register":           None,  # Protected internally by get_current_user

    # Docs — open to all (no auth)
    "/docs":                    None,
    "/openapi":                 None,
    "/redoc":                   None,
}

# Paths that bypass authentication entirely
OPEN_PATHS = {"/docs", "/openapi", "/openapi.json", "/redoc", "/live/health", "/auth/login"}


def _role_rank(role: str) -> int:
    """Returns the numerical rank of a role. Higher = more access."""
    try:
        return ROLES.index(role)
    except ValueError:
        return -1  # Unknown role


def check_permission(user_role: str, required_role: str) -> bool:
    """Returns True if the user's role meets or exceeds the required role."""
    if required_role is None:
        return True
    return _role_rank(user_role) >= _role_rank(required_role)


def get_required_role(path: str) -> Optional[str]:
    """
    Determines the minimum role required for a given request path.
    Returns None for open paths, 'driver' as the default minimum.
    """
    # Check exact and prefix matches
    for prefix, role in ENDPOINT_PERMISSIONS.items():
        if path.startswith(prefix):
            return role

    # Default: require at least driver role
    return "driver"


def _extract_role_from_jwt(token: str) -> Optional[str]:
    """Attempt to extract role from a JWT token without raising."""
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[os.getenv("JWT_ALGORITHM", "HS256")])
        return payload.get("role")
    except Exception:
        return None


class RBACMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that enforces role-based access control.

    Authentication methods (in order):
    1. Authorization: Bearer <jwt> → role extracted from token
    2. X-User-Role header → direct role (dev mode only, when JWT_SECRET="dev")
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for open paths
        for open_path in OPEN_PATHS:
            if path.startswith(open_path):
                return await call_next(request)

        # Determine required role for this endpoint
        required_role = get_required_role(path)
        if required_role is None:
            return await call_next(request)

        # ── Extract user role ────────────────────────────────────────

        user_role = None

        # Method 1: JWT Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user_role = _extract_role_from_jwt(token)

        # Method 2: X-User-Role header (dev fallback)
        if not user_role and JWT_SECRET == "dev":
            user_role = request.headers.get("X-User-Role", "").lower().strip() or None

        # No role found
        if not user_role:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Not authenticated. Provide a Bearer JWT token"
                             + (" or X-User-Role header (dev mode active)." if JWT_SECRET == "dev" else ".")
                }
            )

        if user_role not in ROLES:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid role '{user_role}'. Must be one of: {', '.join(ROLES)}"}
            )

        # Check permission for this endpoint
        if not check_permission(user_role, required_role):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Role '{user_role}' cannot access {path}. Requires '{required_role}' or higher.",
                    "required_role": required_role,
                    "your_role": user_role
                }
            )

        # Attach role to request state for downstream use
        request.state.user_role = user_role
        return await call_next(request)
