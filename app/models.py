from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, TIMESTAMP, Numeric, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))
    is_admin = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    role = Column(String(50), nullable=False, default='user')
    last_login = Column(TIMESTAMP)
    created_by = Column(String(255))
    is_active = Column(Boolean, default=True)
    fullname = Column(String(255))
    default_polling = Column(Integer, default=10)
    timezone = Column(String(100), default='UTC')
    bio = Column(Text)

    # Relationships
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    paypal_transactions = relationship("PaypalTransaction", back_populates="user", cascade="all, delete-orphan")


class ActiveRaffle(Base):
    __tablename__ = "active_raffle"

    id = Column(Integer, primary_key=True, index=True)
    reddit_link = Column(Text)
    total_spots = Column(Integer)
    cost_per_spot = Column(Integer)
    polling_interval = Column(Integer, default=60)
    participants = Column(JSONB, default=[])
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    username = Column(Text, nullable=False, default='default_user')
    fast_raffle_enabled = Column(Boolean, default=False)
    fast_raffle_start_time = Column(BigInteger)


class RaffleHistory(Base):
    __tablename__ = "raffle_history"

    id = Column(Integer, primary_key=True, index=True)
    raffle_date = Column(TIMESTAMP, nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    reddit_link = Column(Text)
    total_spots = Column(Integer)
    cost_per_spot = Column(Integer)
    participants = Column(JSONB)
    total_owed = Column(Integer)
    total_paid = Column(Integer)
    winner = Column(JSONB)
    created_at = Column(TIMESTAMP, server_default=func.now())
    username = Column(String(255), index=True)
    fast_raffle_enabled = Column(Boolean, default=False)
    fast_raffle_start_time = Column(BigInteger)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    details = Column(Text)
    badge = Column(String(100))
    timestamp = Column(TIMESTAMP, server_default=func.now(), index=True)
    raffle_id = Column(Integer)
    username = Column(String(255))


class PaypalTransaction(Base):
    __tablename__ = "paypal_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    raffle_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(String(100), index=True)
    payer_name = Column(String(255))
    amount = Column(Numeric(10, 2), nullable=False)
    participant_reddit_user = Column(String(255))
    participant_name = Column(String(255))
    email_subject = Column(String(500))
    email_date = Column(TIMESTAMP, index=True)
    processed_at = Column(TIMESTAMP, server_default=func.now())
    match_confidence = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="paypal_transactions")


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")
