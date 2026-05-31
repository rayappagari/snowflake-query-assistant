"""
JWT authentication system.

Supports two auth modes:
    jwt      DATABASE_URL is set — full user database in PostgreSQL, JWT tokens
    password DATABASE_URL absent — legacy APP_PASSWORD gate (unchanged behaviour)

The mode is advertised via GET /auth/mode so the frontend can show the right UI.

Token lifecycle
---------------
POST /auth/login  → {access_token, token_type, expires_in, user}
All protected endpoints  → Authorization: Bearer <token>
Tokens expire after JWT_EXPIRE_HOURS (default 8 hours).

Admin bootstrap
---------------
Set ADMIN_USERNAME + ADMIN_PASSWORD to have the first admin user created
automatically at startup when the users table is empty.  Safe to leave these
env vars set permanently — the check is idempotent.

Environment variables
---------------------
JWT_SECRET_KEY      HMAC-SHA256 signing secret.  A random key is generated
                    at startup when this var is absent, which means tokens are
                    invalidated on every restart — set a stable value in prod.
JWT_EXPIRE_HOURS    Token lifetime in hours (default: 8)
ADMIN_USERNAME      Auto-created admin username (optional)
ADMIN_PASSWORD      Auto-created admin password (optional)
DATABASE_URL        When set, enables JWT mode (see db/postgres.py)
"""

import logging
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from db import postgres

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_raw_secret = os.environ.get("JWT_SECRET_KEY", "")
if not _raw_secret:
    _raw_secret = secrets.token_hex(32)
    warnings.warn(
        "JWT_SECRET_KEY not set — using a random secret. Tokens will be "
        "invalidated on every restart. Set JWT_SECRET_KEY in production.",
        stacklevel=1,
    )

SECRET_KEY: str = _raw_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "8"))


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash *plain* with bcrypt and return the digest string."""
    from passlib.context import CryptContext  # noqa: PLC0415
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    from passlib.context import CryptContext  # noqa: PLC0415
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return _ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(username: str, role: str) -> str:
    """
    Create a signed JWT for *username* with *role*.

    Claims
    ------
    sub     username
    role    user role (e.g. "user" or "admin")
    exp     expiry timestamp
    """
    from jose import jwt  # noqa: PLC0415

    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate *token*.

    Raises
    ------
    HTTPException(401)  when the token is missing, expired, or invalid.
    """
    from jose import JWTError, jwt  # noqa: PLC0415

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    FastAPI dependency that extracts and validates a Bearer token.

    Usage::

        @app.get("/protected")
        def protected(user: dict = Depends(get_current_user)):
            return {"hello": user["sub"]}

    Raises
    ------
    HTTPException(401)  when the Authorization header is absent or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or not Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    return decode_token(token)


def require_role(role: str):
    """
    Return a FastAPI dependency that checks the user has at least *role*.

    Currently only 'admin' is enforced above 'user'.
    """
    def _dep(user: dict = None) -> dict:
        # Caller must pass user from get_current_user
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if role == "admin" and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return user
    return _dep


# ── User management ───────────────────────────────────────────────────────────

def create_user(
    username: str,
    password: str,
    email: str | None = None,
    role: str = "user",
) -> dict[str, Any]:
    """
    Insert a new user into the PostgreSQL users table.

    Parameters
    ----------
    username:   Must be unique (raises 409 if taken).
    password:   Plaintext password — stored as bcrypt hash.
    email:      Optional contact email.
    role:       'user' or 'admin'.

    Raises
    ------
    HTTPException(409)  when the username already exists.
    HTTPException(503)  when PostgreSQL is not available.
    """
    if not postgres.is_available():
        raise HTTPException(status_code=503, detail="User database not available")

    hashed = hash_password(password)
    result = postgres.query(
        "SELECT id FROM users WHERE username = %s",
        (username,),
    )
    if result:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already exists")

    postgres.query(
        """
        INSERT INTO users (username, email, hashed_password, role)
        VALUES (%s, %s, %s, %s)
        """,
        (username, email, hashed, role),
    )
    logger.info("Created user '%s' with role '%s'", username, role)
    return get_user(username)


def get_user(username: str) -> dict[str, Any] | None:
    """
    Fetch a user record by username.

    Returns None if not found or if PostgreSQL is unavailable.
    """
    if not postgres.is_available():
        return None
    rows = postgres.query(
        "SELECT id, username, email, role, created_at, is_active FROM users WHERE username = %s",
        (username,),
    )
    return rows[0] if rows else None


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """
    Verify credentials and return the user dict, or None on failure.

    Checks that the user exists, is_active, and the password matches.
    """
    rows = postgres.query(
        "SELECT username, hashed_password, role, is_active FROM users WHERE username = %s",
        (username,),
    )
    if not rows:
        return None
    user = rows[0]
    if not user.get("is_active"):
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return get_user(username)


def init_admin() -> None:
    """
    Bootstrap an admin user at startup if the table is empty.

    Reads ADMIN_USERNAME and ADMIN_PASSWORD env vars.  Does nothing when:
    - Either env var is absent
    - PostgreSQL is not available
    - The users table already contains at least one row
    """
    admin_user = os.environ.get("ADMIN_USERNAME", "")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_user or not admin_pass:
        return
    if not postgres.is_available():
        logger.warning("ADMIN_USERNAME set but PostgreSQL not available — skipping admin init")
        return

    rows = postgres.query("SELECT COUNT(*) AS cnt FROM users")
    if rows and rows[0].get("cnt", 0) > 0:
        logger.debug("Admin init skipped — users table not empty")
        return

    try:
        create_user(admin_user, admin_pass, role="admin")
        logger.info("Admin user '%s' created", admin_user)
    except HTTPException as exc:
        if exc.status_code == 409:
            logger.debug("Admin user '%s' already exists", admin_user)
        else:
            raise


# ── Pydantic models ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    role: str = "user"


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/mode")
def auth_mode() -> dict:
    """
    Return the current authentication mode.

    The frontend calls this once on init to decide which gate to show.
    ``{"mode": "jwt"}``      → show username/password login form
    ``{"mode": "password"}`` → show legacy APP_PASSWORD gate
    """
    return {"mode": "jwt" if postgres.is_available() else "password"}


@router.post("/login")
def login(req: LoginRequest) -> dict:
    """
    Exchange username + password for a JWT access token.

    Returns
    -------
    access_token   The signed JWT.
    token_type     Always "bearer".
    expires_in     Token lifetime in seconds.
    user           {username, role} sub-object.
    """
    user = authenticate_user(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_token(user["username"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        "user": {"username": user["username"], "role": user["role"]},
    }


@router.post("/register", status_code=201)
def register(
    req: RegisterRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    """
    Create a new user account.  Requires admin role.

    Admins may set the role field to 'admin' to create additional admins.
    """
    # Require authenticated admin
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    caller = decode_token(authorization.split(" ", 1)[1])
    if caller.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    user = create_user(req.username, req.password, email=req.email, role=req.role)
    return {"username": user["username"], "role": user["role"], "email": user.get("email")}


@router.get("/users")
def list_users(authorization: str | None = Header(default=None)) -> list[dict]:
    """Return all users. Admin only."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    caller = decode_token(authorization.split(" ", 1)[1])
    if caller.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    if not postgres.is_available():
        raise HTTPException(status_code=503, detail="User database not available")
    rows = postgres.query(
        "SELECT id, username, email, role, is_active, created_at FROM users ORDER BY created_at DESC"
    )
    return [
        {
            "id": r["id"],
            "username": r["username"],
            "email": r.get("email"),
            "role": r["role"],
            "is_active": r["is_active"],
            "created_at": str(r.get("created_at", "")),
        }
        for r in (rows or [])
    ]


@router.patch("/users/{username}")
def update_user(
    username: str,
    body: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    """Update a user's role or active status. Admin only."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    caller = decode_token(authorization.split(" ", 1)[1])
    if caller.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    if caller.get("sub") == username and "is_active" in body and not body["is_active"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    if not postgres.is_available():
        raise HTTPException(status_code=503, detail="User database not available")

    updates, params = [], []
    if "role" in body:
        updates.append("role = %s"); params.append(body["role"])
    if "is_active" in body:
        updates.append("is_active = %s"); params.append(body["is_active"])
    if "password" in body:
        updates.append("hashed_password = %s"); params.append(hash_password(body["password"]))
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    params.append(username)
    postgres.query(f"UPDATE users SET {', '.join(updates)} WHERE username = %s", tuple(params))
    return get_user(username) or {}


@router.delete("/users/{username}", status_code=204)
def delete_user(
    username: str,
    authorization: str | None = Header(default=None),
) -> None:
    """Delete a user permanently. Admin only. Cannot delete yourself."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    caller = decode_token(authorization.split(" ", 1)[1])
    if caller.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    if caller.get("sub") == username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if not postgres.is_available():
        raise HTTPException(status_code=503, detail="User database not available")
    postgres.query("DELETE FROM users WHERE username = %s", (username,))


@router.get("/me")
def me(authorization: str | None = Header(default=None)) -> dict:
    """Return the current user's profile."""
    user_claims = get_current_user(authorization)
    user = get_user(user_claims["sub"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user.get("email"),
        "created_at": str(user.get("created_at", "")),
    }
