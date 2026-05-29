from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(500), nullable=False)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    base_url = Column(String(500), nullable=False)
    strategy = Column(String(20), nullable=False, default="round_robin")  # round_robin, weighted, random, least_used
    enabled = Column(Boolean, nullable=False, default=True)
    weight = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    keys = relationship("Key", back_populates="channel", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="channel")


class Key(Base):
    __tablename__ = "keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(500), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active, inactive, error
    weight = Column(Integer, nullable=False, default=1)
    last_used = Column(DateTime, nullable=True)
    last_check = Column(DateTime, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    quota_remaining = Column(Float, nullable=True)
    total_requests = Column(Integer, nullable=False, default=0)
    success_requests = Column(Integer, nullable=False, default=0)
    failed_requests = Column(Integer, nullable=False, default=0)
    avg_response_time = Column(Float, nullable=False, default=0.0)
    total_prompt_tokens = Column(Integer, nullable=False, default=0)
    total_completion_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    channel = relationship("Channel", back_populates="keys")
    request_logs = relationship("RequestLog", back_populates="key")


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now())
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    key_id = Column(Integer, ForeignKey("keys.id", ondelete="SET NULL"), nullable=True)
    model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True, default=0)
    completion_tokens = Column(Integer, nullable=True, default=0)
    response_time_ms = Column(Integer, nullable=True, default=0)  # milliseconds
    status_code = Column(Integer, nullable=True)
    is_success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    is_streaming = Column(Boolean, nullable=False, default=False)
    source_ip = Column(String(50), nullable=True)

    channel = relationship("Channel", back_populates="request_logs")
    key = relationship("Key", back_populates="request_logs")