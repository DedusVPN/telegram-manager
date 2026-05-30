from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    session_string = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="account")


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
