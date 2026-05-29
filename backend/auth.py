import os
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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


async def ensure_default_admin(session: AsyncSession):
    """Create default admin user if no admin exists."""
    result = await session.execute(select(AdminUser))
    existing = result.scalar_one_or_none()
    if existing is None:
        hashed = get_password_hash("admin123")
        admin = AdminUser(
            username="admin",
            hashed_password=hashed,
            must_change_password=True,
        )
        session.add(admin)
        await session.commit()
        logger.info("Default admin user created (username=admin, password=admin123)")
    return existing


@router.post("/login")
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    await ensure_default_admin(session)

    result = await session.execute(select(AdminUser).where(AdminUser.username == req.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_password": user.must_change_password,
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

    # Return a new token after password change
    access_token = create_access_token(data={"sub": current_user.username})
    return {
        "message": "Password changed successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_password": False,
    }


@router.get("/me")
async def get_me(current_user: AdminUser = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "must_change_password": current_user.must_change_password,
    }


@router.get("/status")
async def auth_status(session: AsyncSession = Depends(get_session)):
    """Check if auth is initialized (for frontend to know if login is needed)."""
    admin = await ensure_default_admin(session)
    return {"auth_enabled": True, "has_admin": True}