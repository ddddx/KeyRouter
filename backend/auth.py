import os
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import get_session
from models import AdminUser
from config import JWT_SECRET, JWT_EXPIRATION_HOURS, JWT_ALGORITHM

logger = logging.getLogger("auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class SetupRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def _has_any_admin(session: AsyncSession) -> bool:
    """Check if any admin user exists in the database."""
    result = await session.execute(select(func.count(AdminUser.id)))
    count = result.scalar() or 0
    return count > 0


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> AdminUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await session.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/setup")
async def setup_admin(req: SetupRequest, session: AsyncSession = Depends(get_session)):
    """Initialize the first admin account. Only available when no admin exists."""
    if await _has_any_admin(session):
        raise HTTPException(status_code=403, detail="Admin account already exists. Setup is no longer available.")

    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check username uniqueness
    result = await session.execute(select(AdminUser).where(AdminUser.username == req.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed = get_password_hash(req.password)
    admin = AdminUser(
        username=req.username,
        hashed_password=hashed,
        must_change_password=False,
    )
    session.add(admin)
    await session.commit()

    # Auto-login after setup — return JWT token
    access_token = create_access_token(data={"sub": admin.username})
    logger.info(f"First admin user '{admin.username}' created via setup")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": admin.username,
        "message": "Admin account created successfully",
    }


@router.get("/status")
async def auth_status(session: AsyncSession = Depends(get_session)):
    """Check auth initialization status (for frontend routing)."""
    has_admin = await _has_any_admin(session)
    return {"auth_enabled": True, "has_admin": has_admin}


@router.post("/login")
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(AdminUser).where(AdminUser.username == req.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
    }


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: AdminUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.must_change_password = False
    session.add(current_user)
    await session.commit()

    access_token = create_access_token(data={"sub": current_user.username})
    return {
        "message": "Password changed successfully",
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_me(current_user: AdminUser = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "must_change_password": current_user.must_change_password,
    }