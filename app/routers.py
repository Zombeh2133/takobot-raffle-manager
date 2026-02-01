from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import (
    User, ActiveRaffle, RaffleHistory, ActivityLog,
    PaypalTransaction, Settings, PasswordResetToken
)

router = APIRouter(prefix="/api")
# =========================
# User Endpoints
# =========================

@router.get("/users")
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users with pagination"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/username/{username}")
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """Get a user by username"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# =========================
# Raffle History Endpoints
# =========================

@router.get("/raffle/history")
def get_raffle_history(
    skip: int = 0,
    limit: int = 50,
    username: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get raffle history with filters"""
    query = db.query(RaffleHistory)

    if username:
        query = query.filter(RaffleHistory.username == username)

    if status:
        query = query.filter(RaffleHistory.status == status)

    raffles = query.order_by(RaffleHistory.raffle_date.desc()).offset(skip).limit(limit).all()
    
    # Format to match Node.js response structure
    history = []
    for raffle in raffles:
        history.append({
            "id": raffle.id,
            "date": raffle.raffle_date.isoformat() if raffle.raffle_date else None,
            "status": raffle.status,
            "redditLink": raffle.reddit_link,
            "totalSpots": raffle.total_spots,
            "costPerSpot": raffle.cost_per_spot,
            "participants": raffle.participants,
            "totalOwed": float(raffle.total_owed) if raffle.total_owed else 0,
            "totalPaid": float(raffle.total_paid) if raffle.total_paid else 0,
            "winner": raffle.winner,
            "username": raffle.username
        })
    
    return {"ok": True, "data": history}

@router.get("/raffle/load")
def load_active_raffle(db: Session = Depends(get_db)):
    """Load the current active raffle"""
    active_raffle = db.query(ActiveRaffle).first()
    
    if not active_raffle:
        return {"ok": True, "data": None}
    
    return {
        "ok": True,
        "data": {
            "id": active_raffle.id,
            "reddit_link": active_raffle.reddit_link,
            "total_spots": active_raffle.total_spots,
            "cost_per_spot": active_raffle.cost_per_spot,
            "polling_interval": active_raffle.polling_interval,
            "participants": active_raffle.participants or [],
            "status": "active",
            "username": active_raffle.username,
            "created_at": active_raffle.created_at.isoformat() if active_raffle.created_at else None,
            "updated_at": active_raffle.updated_at.isoformat() if active_raffle.updated_at else None,
            "fast_raffle_enabled": active_raffle.fast_raffle_enabled,
            "fast_raffle_start_time": active_raffle.fast_raffle_start_time
        }
    }

@router.get("/raffle/history/{raffle_id}")
def get_raffle_by_id(raffle_id: int, db: Session = Depends(get_db)):
    """Get a specific raffle from history"""
    raffle = db.query(RaffleHistory).filter(RaffleHistory.id == raffle_id).first()
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")
    return raffle


# =========================
# Activity Log 
# =========================

@router.get("/activity/list")
def get_activity_list(
    skip: int = 0,
    limit: int = 100,
    activity_type: Optional[str] = None,
    username: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get activity log with filters"""
    query = db.query(ActivityLog)

    if activity_type:
        query = query.filter(ActivityLog.type == activity_type)

    if username:
        query = query.filter(ActivityLog.username == username)

    activities = query.order_by(ActivityLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Format to match Node.js response structure
    activity_list = []
    for activity in activities:
        activity_list.append({
            "id": activity.id,
            "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
            "type": activity.type,
            "title": activity.title,
            "details": activity.details,
            "badge": activity.badge,
            "username": activity.username,
            "raffleId": activity.raffle_id
        })
    
    return {"ok": True, "data": activity_list}

@router.delete("/activity/clear")
def clear_activity_log(
    username: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Clear activity log (optionally filtered by username)"""
    try:
        query = db.query(ActivityLog)
        
        if username:
            query = query.filter(ActivityLog.username == username)
            deleted_count = query.delete(synchronize_session=False)
            db.commit()
            return {
                "ok": True, 
                "message": f"Cleared {deleted_count} activities for {username}"
            }
        else:
            # Clear all activities if no username specified
            deleted_count = query.delete(synchronize_session=False)
            db.commit()
            return {
                "ok": True,
                "message": f"Cleared {deleted_count} activities"
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================
# PayPal Transaction Endpoints
# ============================

@router.get("/transactions")
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    raffle_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get PayPal transactions with filters"""
    query = db.query(PaypalTransaction)
    
    if user_id:
        query = query.filter(PaypalTransaction.user_id == user_id)
    
    if raffle_id:
        query = query.filter(PaypalTransaction.raffle_id == raffle_id)
    
    transactions = query.order_by(PaypalTransaction.email_date.desc()).offset(skip).limit(limit).all()
    return transactions


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get a specific transaction by ID"""
    transaction = db.query(PaypalTransaction).filter(PaypalTransaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


# =========================
# Settings Endpoints
# =========================

@router.get("/settings")
def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings"""
    settings = db.query(Settings).all()
    return settings


@router.get("/settings/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    """Get a specific setting by key"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


# =========================
# Statistics Endpoints
# =========================

@router.get("/stats/overview")
def get_stats_overview(db: Session = Depends(get_db)):
    """Get overall statistics"""
    total_users = db.query(User).count()
    total_raffles = db.query(RaffleHistory).count()
    active_raffles = db.query(ActiveRaffle).count()
    total_transactions = db.query(PaypalTransaction).count()
    
    # Get total revenue
    from sqlalchemy import func
    total_revenue = db.query(func.sum(PaypalTransaction.amount)).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_raffles": total_raffles,
        "active_raffles": active_raffles,
        "total_transactions": total_transactions,
        "total_revenue": float(total_revenue)
    }


@router.get("/stats/user/{username}")
def get_user_stats(username: str, db: Session = Depends(get_db)):
    """Get statistics for a specific user"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    raffles_hosted = db.query(RaffleHistory).filter(RaffleHistory.username == username).count()
    transactions = db.query(PaypalTransaction).filter(PaypalTransaction.user_id == user.id).count()
    
    from sqlalchemy import func
    total_revenue = db.query(func.sum(PaypalTransaction.amount)).filter(
        PaypalTransaction.user_id == user.id
    ).scalar() or 0
    
    return {
        "username": username,
        "raffles_hosted": raffles_hosted,
        "total_transactions": transactions,
        "total_revenue": float(total_revenue),
        "member_since": user.created_at,
        "last_login": user.last_login
    }

