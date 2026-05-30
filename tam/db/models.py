from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True)
    protocol = Column(String, nullable=False, default="socks5")
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String)
    password = Column(String)
    label = Column(String)
    is_active = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=True)
    fail_count = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    last_checked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    session_string = Column(Text, nullable=False)
    proxy_id = Column(Integer, ForeignKey("proxies.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    proxy = relationship("Proxy")
    messages = relationship("Message", back_populates="account")


class RegistrationJob(Base):
    __tablename__ = "registration_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String, default="pending")
    proxy_id = Column(Integer, ForeignKey("proxies.id"))
    delay_seconds = Column(Integer, default=3)
    default_2fa_password = Column(String)
    total_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    proxy = relationship("Proxy")
    items = relationship("RegistrationItem", back_populates="job", cascade="all, delete-orphan")


class RegistrationItem(Base):
    __tablename__ = "registration_items"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("registration_jobs.id"), nullable=False)
    phone = Column(String, nullable=False)
    status = Column(String, default="pending")
    proxy_id = Column(Integer, ForeignKey("proxies.id"))
    auth_session_id = Column(String)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    job = relationship("RegistrationJob", back_populates="items")
    proxy = relationship("Proxy")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    target_chat = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String, default="pending")
    sent_at = Column(DateTime)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="messages")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    target_chat = Column(String, nullable=False)
    message_text = Column(Text, nullable=False)
    account_ids = Column(String, nullable=False)
    repeat_count = Column(Integer, default=1)
    interval = Column(Integer, default=30)
    account_delay = Column(Integer, default=10)
    scheduled_time = Column(DateTime)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
