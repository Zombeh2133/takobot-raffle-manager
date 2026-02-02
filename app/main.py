from fastapi import FastAPI, Request, UploadFile, File, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from pathlib import Path
from PIL import Image
from datetime import datetime, timedelta
from . import reddit as Reddit
import json
import sqlite3
import os
import hashlib
import base64
import secrets
import bcrypt
import httpx
import subprocess
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables only.")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

app = FastAPI()
# =========================
# Sessions (cookie-based)
# =========================
SESSION_SECRET = os.environ.get("SESSION_SECRET", "CHANGE_ME_SESSION_SECRET")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=False)

# =========================
# Paths
# =========================
APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_DIR = DATA_DIR / "users"

# =========================
# PostgreSQL Connection
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:makii@localhost:5432/raffle_manager")

# =========================
# Email Configuration (Gmail SMTP)
# =========================
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "littlesharksaba@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")  # Gmail app password
EMAIL_FROM = os.environ.get("EMAIL_FROM", EMAIL_USER)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8000")

def get_pg_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =========================
# Templates + Static
# =========================
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# =========================
# Image paths
# =========================
SOURCE_IMG = STATIC_DIR / "assets" / "Background" / "Sidebar.png"
OUTPUT_IMG = STATIC_DIR / "processed" / "sidebar_processed.png"

# =========================
# DB helpers
# =========================
def db_connect():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con

def ensure_db():
    con = db_connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       username TEXT UNIQUE NOT NULL,
       password_hash TEXT
    )
    """)

    con.commit()
    con.close()

@app.on_event("startup")
async def on_startup():
    """Initialize on startup"""
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure password_hash column exists in PostgreSQL
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
        """)
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
        """)
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by TEXT;
        """)
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
        """)
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
        """)
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
        """)
        # Remove NOT NULL constraint from email column (make it optional)
        cur.execute("""
            ALTER TABLE users ALTER COLUMN email DROP NOT NULL;
        """)
        
        # Create raffles table in PostgreSQL
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raffles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                status TEXT NOT NULL DEFAULT 'active',
                reddit_post_url TEXT DEFAULT '',
                total_spots INTEGER DEFAULT 0,
                cost_per_spot NUMERIC(10,2) DEFAULT 0,
                fast_raffle_enabled BOOLEAN DEFAULT FALSE,
                fast_raffle_start_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create participants table in PostgreSQL
        cur.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id SERIAL PRIMARY KEY,
                raffle_id INTEGER NOT NULL REFERENCES raffles(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                spots_requested INTEGER DEFAULT 0,
                spots_assigned TEXT DEFAULT '',
                amount_owed NUMERIC(10,2) DEFAULT 0,
                amount_paid NUMERIC(10,2) DEFAULT 0,
                payment_status TEXT DEFAULT 'pending',
                request_link TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Startup DB migration info: {e}")

def get_current_user(request: Request):
    """Get current user from session (PostgreSQL)"""
    uid = request.session.get("user_id")
    if not uid:
        return None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, is_admin FROM users WHERE id = %s", (uid,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None

def get_or_create_active_raffle_id(user_id: int) -> int:
    """Get or create an active raffle for the user in PostgreSQL"""
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM active_raffle
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()

    if row:
        conn.close()
        return int(row["id"])

    cur.execute("""
        INSERT INTO active_raffle (user_id, reddit_link, participants)
        VALUES (%s, '', '[]'::jsonb)
        RETURNING id
    """, (user_id,))
    new_row = cur.fetchone()
    conn.commit()
    conn.close()
    return int(new_row["id"])

def get_active_raffle_id(user_id: int):
    """Get active raffle ID for the user WITHOUT creating one (returns None if not found)"""
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM active_raffle
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    
    return int(row["id"]) if row else None

def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def db_init_raffle_tables():
    con = db_connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS raffles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        reddit_post_url TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raffle_id INTEGER NOT NULL,
        reddit_comment_id TEXT NOT NULL,
        reddit_author TEXT NOT NULL,
        comment_body TEXT NOT NULL,
        spots INTEGER NULL,
        created_utc INTEGER NOT NULL DEFAULT 0,
        permalink TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(raffle_id, reddit_comment_id)
    )
    """)

    con.commit()
    con.close()

# =========================
# Password hashing (PBKDF2)
# =========================
def hash_password(password: str) -> str:
    # format: pbkdf2$iterations$salt_b64$hash_b64
    iterations = 200_000
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )
def verify_password(password: str, stored: str) -> bool:
    """Verify password against stored hash - supports both bcrypt and pbkdf2"""
    try:
        # Check if it's a bcrypt hash (starts with $2a$, $2b$, $2y$)
        if stored.startswith('$2'):
            # bcrypt format (from Node.js)
            return bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))

        # Otherwise try pbkdf2 format (from FastAPI)
        scheme, iters, salt_b64, hash_b64 = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False
        iterations = int(iters)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(dk, expected)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

# =========================
# Raffle API Endpoints
# =========================
@app.post("/api/raffle/save")
async def save_raffle(request: Request):
    """Save raffle data to PostgreSQL database"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    try:
        body = await request.json()
        raffle_id = get_or_create_active_raffle_id(user["id"])
        
        print(f"[SAVE] Saving raffle_id={raffle_id} for user={user['username']}")
        print(f"[SAVE] Data: redditLink={body.get('redditLink')}, totalSpots={body.get('totalSpots')}, participants={len(body.get('participants', []))}")
        
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Convert fastRaffleStartTime to bigint if present
        fast_raffle_start_time = body.get("fastRaffleStartTime")
        if fast_raffle_start_time and isinstance(fast_raffle_start_time, str):
            # Convert ISO string to Unix timestamp (milliseconds)
            from datetime import datetime
            dt = datetime.fromisoformat(fast_raffle_start_time.replace('Z', '+00:00'))
            fast_raffle_start_time = int(dt.timestamp() * 1000)
        
        # Update raffle in active_raffle table
        cur.execute("""
            UPDATE active_raffle
            SET reddit_link = %s, total_spots = %s, cost_per_spot = %s,
                fast_raffle_enabled = %s, fast_raffle_start_time = %s,
                participants = %s::jsonb, updated_at = NOW()
            WHERE id = %s
        """, (
            body.get("redditLink", ""),
            body.get("totalSpots", 0),
            body.get("costPerSpot", 0),
            body.get("fastRaffleEnabled", False),
            fast_raffle_start_time,
            json.dumps(body.get("participants", [])),
            raffle_id
        ))
        
        print(f"[SAVE] Updated active_raffle with {len(body.get('participants', []))} participants")
        
        conn.commit()
        conn.close()
        
        print(f"[SAVE] Successfully saved raffle_id={raffle_id}")
        
        return {"ok": True, "raffle_id": raffle_id}
    except Exception as e:
        print(f"[SAVE] Error saving raffle: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/raffle/load")
async def load_raffle(request: Request):
    """Load active raffle data from PostgreSQL database"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    try:
        # ✅ FIX: Only GET raffle, don't create if it doesn't exist
        raffle_id = get_active_raffle_id(user["id"])
        
        # If no active raffle exists, return None (user hasn't clicked "Save Setup" yet)
        if raffle_id is None:
            print(f"[LOAD] No active raffle found for user={user['username']}")
            return {"ok": True, "data": None}
        
        print(f"[LOAD] Loading raffle_id={raffle_id} for user={user['username']}")
        
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Get raffle from active_raffle table
        cur.execute("""
            SELECT id, reddit_link, total_spots, cost_per_spot,
                   fast_raffle_enabled, fast_raffle_start_time, participants
            FROM active_raffle
            WHERE id = %s
        """, (raffle_id,))
        raffle_row = cur.fetchone()
        
        print(f"[LOAD] Found raffle_row: {raffle_row}")
        
        conn.close()
        
        if not raffle_row:
            print(f"[LOAD] No raffle found for id={raffle_id}")
            return {"ok": True, "data": None}
        
        # Parse participants from JSONB
        participants = raffle_row["participants"] if raffle_row["participants"] else []
        
        print(f"[LOAD] Found {len(participants)} participants")
        
        # Convert fast_raffle_start_time from bigint (Unix timestamp ms) to ISO string
        fast_raffle_start_time = None
        if raffle_row["fast_raffle_start_time"]:
            from datetime import datetime
            dt = datetime.fromtimestamp(raffle_row["fast_raffle_start_time"] / 1000)
            fast_raffle_start_time = dt.isoformat() + "Z"
        
        raffle = {
            "id": raffle_id,
            "redditLink": raffle_row["reddit_link"] or "",
            "totalSpots": raffle_row["total_spots"] or 0,
            "costPerSpot": float(raffle_row["cost_per_spot"]) if raffle_row["cost_per_spot"] else 0,
            "fastRaffleEnabled": raffle_row["fast_raffle_enabled"] or False,
            "fastRaffleStartTime": fast_raffle_start_time,
            "participants": participants
        }
        
        print(f"[LOAD] Returning raffle data: redditLink={raffle['redditLink']}, totalSpots={raffle['totalSpots']}, participants={len(participants)}")
        
        return {"ok": True, "data": raffle}
    except Exception as e:
        print(f"[LOAD] Error loading raffle: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.delete("/api/raffle/clear")
async def clear_active_raffle(request: Request):
    """
    Clear the active raffle for the current user
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Get the active raffle ID for this user
        cur.execute("SELECT id FROM active_raffle WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user["id"],))
        raffle_row = cur.fetchone()
        
        if raffle_row:
            raffle_id = raffle_row["id"]
            
            # Delete the raffle from active_raffle table
            cur.execute("DELETE FROM active_raffle WHERE id = %s", (raffle_id,))
            
            conn.commit()
            print(f"[CLEAR] Deleted raffle {raffle_id} and its participants for user {user['username']}")
        else:
            print(f"[CLEAR] No active raffle found for user {user['username']}")
        
        conn.close()
        
        return {"ok": True}
    except Exception as e:
        print(f"[CLEAR] Error clearing raffle: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# =========================
# Admin API (check is_admin from PostgreSQL)
# =========================
@app.get("/api/admin/users")
async def admin_list_users(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

    if not user.get("is_admin"):
        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)

    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, is_admin, email, created_at, created_by, last_login FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()

        items = []
        for r in rows:
            uid = int(r["id"])
            creds_dir = str(USERS_DIR / str(uid) / "credentials")
            oauth_path = str(USERS_DIR / str(uid) / "credentials" / "gmail_oauth_client.json")
            
            # Convert is_admin to role string
            role = "admin" if r["is_admin"] else "user"
            
            items.append({
                "id": uid,
                "username": r["username"],
                "is_admin": r["is_admin"],
                "role": role,
                "email": r.get("email"),
                "created_at": r.get("created_at").isoformat() if r.get("created_at") else None,
                "created_by": r.get("created_by"),
                "last_login": r.get("last_login").isoformat() if r.get("last_login") else None,
                "creds_dir": creds_dir,
                "gmail_oauth_client_path": oauth_path,
            })

        return {"ok": True, "users": items}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/admin/users")
async def admin_create_user(request: Request):
    """Create a new user (admin only)"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    if not user.get("is_admin"):
        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    
    try:
        body = await request.json()
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()
        email = body.get("email", "").strip()
        is_admin = body.get("role") == "admin"
        
        if not username or not password:
            return JSONResponse({"ok": False, "error": "Username and password required"}, status_code=400)
        
        if len(password) < 8:
            return JSONResponse({"ok": False, "error": "Password must be at least 8 characters"}, status_code=400)
        
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            conn.close()
            return JSONResponse({"ok": False, "error": "Username already exists"}, status_code=409)
        
        # Hash password using bcrypt
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert new user
        cur.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
            (username, hashed, is_admin, user.get("username"))
        )
        new_user_id = cur.fetchone()["id"]
        conn.commit()
        conn.close()
        
        # Create user directory structure
        user_dir = USERS_DIR / str(new_user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "credentials").mkdir(exist_ok=True)
        
        return {"ok": True, "data": {"id": new_user_id, "username": username, "is_admin": is_admin}}
    except Exception as e:
        print(f"Error creating user: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.put("/api/admin/users/{user_id}")
async def admin_update_user(request: Request, user_id: int):
    """Update user role/admin status (admin only)"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    if not user.get("is_admin"):
        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    
    try:
        body = await request.json()
        role = body.get("role", "").strip().lower()
        
        if role not in ["user", "admin", "moderator"]:
            return JSONResponse({"ok": False, "error": "Invalid role"}, status_code=400)
        
        is_admin = (role == "admin")
        
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        target_user = cur.fetchone()
        if not target_user:
            conn.close()
            return JSONResponse({"ok": False, "error": "User not found"}, status_code=404)
        
        # Update user
        cur.execute("UPDATE users SET is_admin = %s WHERE id = %s", (is_admin, user_id))
        conn.commit()
        conn.close()
        
        return {"ok": True, "data": {"id": user_id, "role": role, "is_admin": is_admin}}
    except Exception as e:
        print(f"Error updating user: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    """Delete/deactivate a user (admin only)"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    if not user.get("is_admin"):
        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    
    # Prevent self-deletion
    if user.get("user_id") == user_id:
        return JSONResponse({"ok": False, "error": "Cannot delete your own account"}, status_code=400)
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        target_user = cur.fetchone()
        if not target_user:
            conn.close()
            return JSONResponse({"ok": False, "error": "User not found"}, status_code=404)
        
        # Delete user
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        
        return {"ok": True, "data": {"id": user_id, "deleted": True}}
    except Exception as e:
        print(f"Error deleting user: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# ✅ NEW: Admin Get All Raffles (Active + History)
@app.get("/api/admin/all-raffles")
async def admin_get_all_raffles(request: Request):
    """Proxy to Node.js to get all raffles (active + history combined)"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    if not user.get("is_admin"):
        return JSONResponse({"ok": False, "error": "Admin access required"}, status_code=403)
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:3001/api/admin/all-raffles",
                headers={
                    "X-User-Id": str(user["id"]),
                    "X-User-Name": user["username"],
                    "X-User-Is-Admin": "true" if user.get("is_admin") else "false"
                },
                timeout=30.0
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        print(f"Error fetching all raffles: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# ✅ NEW: Admin Delete Any Raffle (Active or History)
@app.delete("/api/admin/delete-raffle")
async def admin_delete_any_raffle(request: Request):
    """Proxy to Node.js to delete any raffle (active or history)"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    
    if not user.get("is_admin"):
        return JSONResponse({"ok": False, "error": "Admin access required"}, status_code=403)
    
    try:
        body = await request.json()
        raffle_id = body.get("id")
        raffle_type = body.get("type")
        
        if not raffle_id or not raffle_type:
            return JSONResponse({"ok": False, "error": "ID and type are required"}, status_code=400)
        
        import httpx
        import json as json_lib
        async with httpx.AsyncClient() as client:
            # Use request() method instead of delete() since httpx.delete() doesn't support json/content
            response = await client.request(
                "DELETE",
                "http://localhost:3001/api/admin/delete-raffle",
                headers={
                    "X-User-Id": str(user["id"]),
                    "X-User-Name": user["username"],
                    "X-User-Is-Admin": "true" if user.get("is_admin") else "false",
                    "Content-Type": "application/json"
                },
                content=json_lib.dumps({"id": raffle_id, "type": raffle_type}),
                timeout=30.0
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        print(f"Error deleting raffle: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/whoami")
async def whoami(request: Request):
    user = get_current_user(request)
    if not user:
        return {"ok": False, "user": None}
    return {"ok": True, "user": user}

@app.get("/api/auth/current-user")
async def current_user(request: Request):
    """Get current user with admin status - for frontend auth checks"""
    user = get_current_user(request)
    if not user:
        return {"ok": False, "data": None}
    return {
        "ok": True,
        "data": {
            "id": user["id"],
            "username": user["username"],
            "isAdmin": user.get("is_admin", False)
        }
    }

@app.post("/api/auth/logout")
@app.get("/api/auth/logout")
async def api_auth_logout(request: Request):
    """Auth API endpoint for logout - clears session and returns JSON"""
    request.session.clear()
    return {"ok": True, "message": "Logged out successfully"}

# =========================
# API: Upload Gmail OAuth (per-user, numeric folder)
# =========================
@app.post("/api/settings/upload-gmail-oauth")
async def upload_gmail_oauth(request: Request, file: UploadFile = File(...)):
    try:
        user = get_current_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

        if not file.filename.lower().endswith(".json"):
            return JSONResponse({"ok": False, "error": "Please upload a .json file."}, status_code=400)

        raw = await file.read()

        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            return JSONResponse({"ok": False, "error": "Invalid JSON file."}, status_code=400)

        if not isinstance(obj, dict) or ("installed" not in obj and "web" not in obj):
            return JSONResponse(
                {"ok": False, "error": "JSON does not look like a Google OAuth client credentials file."},
                status_code=400
            )

        # Store in /data/users/{username}/gmail_credentials.json
        username = user["username"]
        user_creds_dir = USERS_DIR / username
        user_creds_dir.mkdir(parents=True, exist_ok=True)

        out_path = user_creds_dir / "gmail_credentials.json"
        out_path.write_bytes(raw)

        return {
            "ok": True,
            "saved_to": str(out_path),
            "user_id": user["id"],
            "username": user["username"],
        }

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# =========================
# API: Initiate Gmail OAuth Flow
# =========================
@app.post("/api/settings/gmail-oauth-init")
async def gmail_oauth_init(request: Request):
    """Initiate Gmail OAuth flow - returns authorization URL"""
    try:
        user = get_current_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

        username = user["username"]
        
        # Import gmail_scanner functions
        from . import gmail_scanner
        
        # Get OAuth URL
        result = gmail_scanner.get_oauth_url(username)
        
        return {
            "ok": True,
            "auth_url": result["auth_url"],
            "redirect_uri": result["redirect_uri"]
        }

    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "error": "Please upload Gmail OAuth credentials first"}, status_code=400)
    except Exception as e:
        import traceback
        return JSONResponse({
            "ok": False, 
            "error": str(e),
            "trace": traceback.format_exc()
        }, status_code=500)

# =========================
# API: Complete Gmail OAuth Flow
# =========================
@app.post("/api/settings/gmail-oauth-complete")
async def gmail_oauth_complete(request: Request):
    """Complete Gmail OAuth flow with authorization code"""
    try:
        user = get_current_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

        username = user["username"]
        
        # Get authorization response from request body
        body = await request.json()
        authorization_response = body.get("authorization_response")
        
        if not authorization_response:
            return JSONResponse({"ok": False, "error": "authorization_response is required"}, status_code=400)
        
        # Import gmail_scanner functions
        from . import gmail_scanner
        
        # Complete OAuth flow
        result = gmail_scanner.complete_oauth_flow(username, authorization_response)
        
        return {
            "ok": True,
            "message": "Gmail OAuth authorization completed successfully",
            "result": result
        }

    except Exception as e:
        import traceback
        return JSONResponse({
            "ok": False, 
            "error": str(e),
            "trace": traceback.format_exc()
        }, status_code=500)

# =========================
# API: Delete Gmail OAuth credentials
# =========================
@app.post("/api/settings/delete-gmail-oauth")
async def delete_gmail_oauth(request: Request):
    try:
        user = get_current_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

        username = user["username"]
        user_creds_dir = USERS_DIR / username

        # Delete gmail_credentials.json
        credentials_path = user_creds_dir / "gmail_credentials.json"
        token_path = user_creds_dir / "token.json"

        deleted_files = []

        if credentials_path.exists():
            credentials_path.unlink()
            deleted_files.append("gmail_credentials.json")

        if token_path.exists():
            token_path.unlink()
            deleted_files.append("token.json")

        if not deleted_files:
            return JSONResponse({"ok": False, "error": "No Gmail OAuth credentials found"}, status_code=404)

        return {
            "ok": True,
            "message": f"Deleted {', '.join(deleted_files)}",
            "deleted_files": deleted_files
        }

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# =========================
# API: Scan Gmail for PayPal Payments
# =========================
@app.post("/api/paypal/scan")
async def scan_paypal_emails(request: Request):
    """
    Scan Gmail for PayPal payment emails and match to active raffle participants
    """
    try:
        user = get_current_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

        # Get request body
        body = await request.json()
        raffle_id = body.get("raffle_id")
        since_timestamp = body.get("since_timestamp")  # ISO 8601 timestamp
        days_back = body.get("days_back", 7)  # Fallback if no timestamp

        if not raffle_id:
            return JSONResponse({"ok": False, "error": "raffle_id is required"}, status_code=400)

        # Import and run scanner
        from . import gmail_scanner

        # Use timestamp if provided, otherwise use days_back
        if since_timestamp:
            result = gmail_scanner.scan_and_match_payments(user["username"], raffle_id, since_timestamp=since_timestamp)
        else:
            result = gmail_scanner.scan_and_match_payments(user["username"], raffle_id, days_back=days_back)

        return JSONResponse(result)

    except Exception as e:
        import traceback
        return JSONResponse({
            "ok": False,
            "error": f"Failed to scan emails: {str(e)}",
            "trace": traceback.format_exc()
        }, status_code=500)

@app.post("/api/paypal/clear")
async def clear_paypal_transactions(request: Request):
    """
    Clear all processed PayPal transaction records for a raffle
    This allows emails to be rescanned
    """
    try:
        user = get_current_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

        # Get request body
        body = await request.json()
        raffle_id = body.get("raffle_id")

        if not raffle_id:
            return JSONResponse({"ok": False, "error": "raffle_id is required"}, status_code=400)

        # Delete transaction records for this raffle
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM paypal_transactions
            WHERE user_id = (SELECT id FROM users WHERE username = %s)
              AND raffle_id = %s
        """, (user["username"], raffle_id))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return JSONResponse({
            "ok": True,
            "message": f"Cleared {deleted_count} processed email records",
            "deleted": deleted_count
        })

    except Exception as e:
        import traceback
        return JSONResponse({
            "ok": False,
            "error": f"Failed to clear records: {str(e)}",
            "trace": traceback.format_exc()
        }, status_code=500)

from pydantic import BaseModel
from fastapi import HTTPException

# =========================
# Auth routes
# =========================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    page = TEMPLATES_DIR / "pages" / "login.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>login.html not found</h1><p>Create: app/templates/pages/login.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/login.html", {"request": request, "error": None})

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return templates.TemplateResponse(
                "pages/login.html",
                {"request": request, "error": "Invalid username or password"},
                status_code=401
            )

        # If password_hash exists, enforce it; otherwise fallback (older rows)
        stored = row["password_hash"]
        if stored:
            if not verify_password(password, stored):
                return templates.TemplateResponse(
                    "pages/login.html",
                    {"request": request, "error": "Invalid username or password"},
                    status_code=401
                )

        request.session["user_id"] = int(row["id"])
        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "pages/login.html",
            {"request": request, "error": f"Login error: {e}"},
            status_code=500
        )

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    """Privacy Policy page"""
    page = TEMPLATES_DIR / "pages" / "privacy.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>privacy.html not found</h1><p>Create: app/templates/pages/privacy.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/privacy.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    """Terms of Service page"""
    page = TEMPLATES_DIR / "pages" / "terms.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>terms.html not found</h1><p>Create: app/templates/pages/pages/terms.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/terms.html", {"request": request})

@app.post("/api/auth/login")
async def api_login(request: Request, username: str = Body(...), password: str = Body(...)):
    """JSON API endpoint for login (used by frontend JavaScript)"""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return JSONResponse(
                {"ok": False, "error": "Invalid username or password"},
                status_code=401
            )

        # If password_hash exists, enforce it; otherwise fallback (older rows)
        stored = row["password_hash"]
        if stored:
            if not verify_password(password, stored):
                return JSONResponse(
                    {"ok": False, "error": "Invalid username or password"},
                    status_code=401
                )

        # Set session cookie
        request.session["user_id"] = int(row["id"])

        # Return success with user data
        return JSONResponse({
            "ok": True,
            "data": {
                "id": row["id"],
                "username": row["username"],
                "is_admin": row["is_admin"]
            }
        })
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"Login error: {e}"},
            status_code=500
        )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    page = TEMPLATES_DIR / "pages" / "register.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>register.html not found</h1><p>Create: app/templates/pages/register.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/register.html", {"request": request, "error": None})

@app.post("/register")
async def register_post(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip()

    # Simple username rules (safe + predictable)
    if len(username) < 3 or len(username) > 24:
        return templates.TemplateResponse(
            "pages/register.html",
            {"request": request, "error": "Username must be 3–24 characters."},
            status_code=400
        )
    if not all(c.isalnum() or c in ("-", "_") for c in username):
        return templates.TemplateResponse(
            "pages/register.html",
            {"request": request, "error": "Username can only contain letters, numbers, - or _."},
            status_code=400
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            "pages/register.html",
            {"request": request, "error": "Password must be at least 6 characters."},
            status_code=400
        )

    pw_hash = hash_password(password)

    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        # Insert with default is_admin=false
        cur.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (%s, %s, %s, NOW()) RETURNING id",
            (username, pw_hash, False)
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        conn.close()

        request.session["user_id"] = int(new_id)
        return RedirectResponse(url="/dashboard", status_code=303)
    except psycopg2.IntegrityError:
        return templates.TemplateResponse(
            "pages/register.html",
            {"request": request, "error": "That username is already taken."},
            status_code=400
        )
    except Exception as e:
        return templates.TemplateResponse(
            "pages/register.html",
            {"request": request, "error": f"Registration error: {e}"},
            status_code=500
        )

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/api/logout")
@app.get("/api/logout")
async def api_logout(request: Request):
    """API endpoint for logout - clears session and returns JSON"""
    request.session.clear()
    return {"ok": True, "message": "Logged out successfully"}

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Forgot password page"""
    page = TEMPLATES_DIR / "pages" / "forgot-password.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>forgot-password.html not found</h1><p>Create: app/templates/pages/forgot-password.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/forgot-password.html", {"request": request})

@app.get("/forgot-password.html", response_class=HTMLResponse)
async def forgot_password_page_html(request: Request):
    """Forgot password page (with .html extension)"""
    page = TEMPLATES_DIR / "pages" / "forgot-password.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>forgot-password.html not found</h1><p>Create: app/templates/pages/forgot-password.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/forgot-password.html", {"request": request})

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Reset password page"""
    page = TEMPLATES_DIR / "pages" / "reset-password.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>reset-password.html not found</h1><p>Create: app/templates/pages/reset-password.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/reset-password.html", {"request": request})

@app.get("/reset-password.html", response_class=HTMLResponse)
async def reset_password_page_html(request: Request):
    """Reset password page (with .html extension)"""
    page = TEMPLATES_DIR / "pages" / "reset-password.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>reset-password.html not found</h1><p>Create: app/templates/pages/reset-password.html</p>",
            status_code=404,
        )
    return templates.TemplateResponse("pages/reset-password.html", {"request": request})

# =========================
# Password Reset Email Functions
# =========================
def send_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """Send password reset email via Gmail SMTP"""
    try:
        if not EMAIL_PASSWORD:
            print("❌ ERROR: EMAIL_PASSWORD not set in environment variables!")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🔐 PokemonRaffles - Password Reset Request"
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email

        # Reset URL
        reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"

        # Email HTML body with purple gradient design
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto;">
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2px; border-radius: 12px;">
                <div style="background: white; padding: 40px 30px; border-radius: 10px;">
                  <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #667eea; margin: 0; font-size: 28px;">🎮 PokemonRaffles</h1>
                    <p style="color: #764ba2; margin: 5px 0 0 0; font-size: 14px;">Raffle Management System</p>
                  </div>

                  <h2 style="color: #333; margin-bottom: 20px;">Password Reset Request</h2>

                  <p style="color: #666; line-height: 1.6;">
                    Hello <strong>{username}</strong>,
                  </p>

                  <p style="color: #666; line-height: 1.6;">
                    We received a request to reset your password. Click the button below to create a new password:
                  </p>

                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="display: inline-block;
                              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white;
                              padding: 14px 40px;
                              text-decoration: none;
                              border-radius: 8px;
                              font-weight: bold;
                              font-size: 16px;
                              box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                      Reset My Password
                    </a>
                  </div>

                  <p style="color: #666; font-size: 14px; line-height: 1.6;">
                    Or copy and paste this link into your browser:
                  </p>
                  <p style="color: #667eea; font-size: 13px; word-break: break-all; background: #f8f9ff; padding: 10px; border-radius: 5px;">
                    {reset_url}
                  </p>

                  <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #f0f0f0;">
                    <p style="color: #999; font-size: 13px; margin: 0;">
                      <strong>⏱️ This link will expire in 1 hour.</strong>
                    </p>
                    <p style="color: #999; font-size: 13px; margin: 10px 0 0 0;">
                      If you didn't request this password reset, you can safely ignore this email.
                    </p>
                  </div>

                  <div style="margin-top: 30px; text-align: center;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                      PokemonRaffles Team 🐙<br>
                      Secure Raffle Management for r/PokemonRaffles
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        # Connect to Gmail SMTP and send
        print(f"📧 Connecting to {EMAIL_HOST}:{EMAIL_PORT}...")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()

        print(f"🔐 Logging in as {EMAIL_USER}...")
        server.login(EMAIL_USER, EMAIL_PASSWORD)

        print(f"📨 Sending password reset email to {to_email}...")
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())

        server.quit()
        print(f"✅ Password reset email sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
        print(f"   Check your Gmail app password in EMAIL_PASSWORD env variable")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False

# =========================
# Password Reset API Endpoints
# =========================
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@app.post("/api/auth/forgot-password")
async def forgot_password_api(data: ForgotPasswordRequest):
    """Request password reset - sends email with reset token"""
    try:
        email = data.email.strip().lower()

        if not email:
            return JSONResponse(
                {"ok": False, "error": "Email is required"},
                status_code=400
            )

        # Find user by email
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email FROM users WHERE LOWER(email) = %s", (email,))
        user = cur.fetchone()

        # Always return success (don't reveal if email exists)
        if not user:
            conn.close()
            print(f"⚠️  No user found with email: {email}")
            return {
                "ok": True,
                "message": "If that email is registered, you'll receive a password reset link shortly."
            }

        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)

        # Save token to database
        cur.execute("""
            INSERT INTO password_reset_tokens (user_id, token, email, expires_at, used)
            VALUES (%s, %s, %s, %s, %s)
        """, (user["id"], reset_token, email, expires_at, False))
        conn.commit()
        conn.close()

        # Send email
        email_sent = send_reset_email(email, reset_token, user["username"])

        if not email_sent:
            print(f"❌ Failed to send email to {email}")
            return JSONResponse(
                {"ok": False, "error": "Failed to send email. Please contact support."},
                status_code=500
            )

        return {
            "ok": True,
            "message": "If that email is registered, you'll receive a password reset link shortly."
        }

    except Exception as e:
        print(f"❌ Forgot password error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"ok": False, "error": "An error occurred. Please try again."},
            status_code=500
        )

@app.post("/api/auth/reset-password")
async def reset_password_api(data: ResetPasswordRequest):
    """Reset password using token from email"""
    try:
        token = data.token
        new_password = data.new_password

        if not token or not new_password:
            return JSONResponse(
                {"ok": False, "error": "Token and new password are required"},
                status_code=400
            )

        if len(new_password) < 6:
            return JSONResponse(
                {"ok": False, "error": "Password must be at least 6 characters"},
                status_code=400
            )

        # Find valid token
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, email, expires_at, used
            FROM password_reset_tokens
            WHERE token = %s
        """, (token,))
        token_record = cur.fetchone()

        if not token_record:
            conn.close()
            return JSONResponse(
                {"ok": False, "error": "Invalid or expired reset link"},
                status_code=400
            )

        # Check if already used
        if token_record["used"]:
            conn.close()
            return JSONResponse(
                {"ok": False, "error": "This reset link has already been used"},
                status_code=400
            )

        # Check if expired
        if datetime.now() > token_record["expires_at"]:
            conn.close()
            return JSONResponse(
                {"ok": False, "error": "This reset link has expired. Please request a new one."},
                status_code=400
            )

        # Hash new password
        pw_hash = hash_password(new_password)

        # Update user password
        cur.execute("""
            UPDATE users
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
        """, (pw_hash, token_record["user_id"]))

        # Mark token as used
        cur.execute("""
            UPDATE password_reset_tokens
            SET used = TRUE
            WHERE id = %s
        """, (token_record["id"],))

        conn.commit()
        conn.close()

        print(f"✅ Password reset successful for user_id: {token_record['user_id']}")

        return {
            "ok": True,
            "message": "Password reset successful! You can now login with your new password."
        }

    except Exception as e:
        print(f"❌ Reset password error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"ok": False, "error": "An error occurred. Please try again."},
            status_code=500
        )

# =========================
# Reddit Scan API (matches frontend)
# =========================
@app.get("/api/reddit/scan")
async def scan_reddit_endpoint(request: Request):
    """Scan Reddit post and extract participants - matches frontend API call"""
    try:
        url = request.query_params.get('url')
        costPerSpot = request.query_params.get('costPerSpot')
        totalSpots = request.query_params.get('totalSpots')  # Optional parameter
        existingCommentIds = request.query_params.get('existingCommentIds')  # Optional: JSON array of comment IDs

        if not url or not costPerSpot:
            return JSONResponse(
                {"ok": False, "error": "Missing url or costPerSpot parameter"},
                status_code=400
            )

        # Use optimized parser if available, fallback to regular parser
        parser_path = APP_DIR.parent / "reddit_parser_optimized.py"
        if not parser_path.exists():
            parser_path = APP_DIR / "reddit_parser.py"

        if not parser_path.exists():
            return JSONResponse(
                {"ok": False, "error": f"Reddit parser not found at {parser_path}"},
                status_code=500
            )

        # Run the Python parser script
        cmd_args = ["python3", str(parser_path), url, costPerSpot]
        if totalSpots:
            cmd_args.append(totalSpots)

        # Pass existing comment IDs to optimized parser (to skip AI calls)
        if existingCommentIds and "optimized" in str(parser_path):
            cmd_args.append(existingCommentIds)

        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=120  # Increased to 120 seconds for large raffle threads
        )

        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return JSONResponse(
                {"ok": False, "error": f"Parser error: {error_msg}"},
                status_code=500
            )

        # Parse the JSON response
        try:
            response_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return JSONResponse(
                {"ok": False, "error": f"Invalid JSON from parser: {str(e)}\nOutput: {result.stdout[:500]}"},
                status_code=500
            )

        # Map 'username' to 'redditUser' for frontend compatibility
        if response_data.get("ok") and "participants" in response_data:
            for participant in response_data["participants"]:
                if "username" in participant:
                    participant["redditUser"] = participant.pop("username")
                # Ensure redditUser exists even if username was missing
                if "redditUser" not in participant:
                    participant["redditUser"] = "unknown"

        return JSONResponse(response_data)

    except subprocess.TimeoutExpired:
        return JSONResponse(
            {"ok": False, "error": "Reddit scan timed out"},
            status_code=500
        )
    except Exception as e:
        import traceback
        return JSONResponse(
            {"ok": False, "error": f"Failed to scan Reddit: {str(e)}\n{traceback.format_exc()}"},
            status_code=500
        )

# =========================
# API Proxy to Node.js Backend
# =========================
# Include Database API Routes
# =========================
from app.routers import router as db_router
app.include_router(db_router)

# =========================
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_nodejs(path: str, request: Request):
    """
    Forward all /api/* requests to Node.js backend on port 3000
    """
    # Skip paths that should be handled by FastAPI router
    FASTAPI_ROUTER_PREFIXES = ["users", "activity", "transactions", "settings", "stats"]
    for prefix in FASTAPI_ROUTER_PREFIXES:
        if path.startswith(prefix):
            raise HTTPException(status_code=404, detail="Route not found in proxy")


    try:
        # Build the target URL
        target_url = f"http://localhost:3001/api/{path}"

        # Get request body if present
        body = await request.body()

        # Get current user from session
        user = get_current_user(request)

        # Debug logging
        print(f"[PROXY] Path: /api/{path}")
        print(f"[PROXY] Session user_id: {request.session.get('user_id')}")
        print(f"[PROXY] Current user: {user}")

        # Prepare headers - add user info for Node.js backend
        headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}

        # Add custom headers with user info (if logged in)
        if user:
            headers["X-User-Id"] = str(user["id"])
            headers["X-User-Name"] = user["username"]
            headers["X-User-Admin"] = "true" if user.get("is_admin") else "false"
            print(f"[PROXY] Adding headers: X-User-Id={user['id']}, X-User-Name={user['username']}, X-User-Admin={user.get('is_admin')}")

        # Forward the request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                timeout=120.0  # Increased to 120 seconds for long-running operations
            )

            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"Proxy error: {str(e)}"},
            status_code=500
        )

# =========================
# JavaScript File Proxy Routes
# Proxy JS files from Node.js backend (port 3000)
# =========================
from fastapi.responses import Response

@app.get("/background-polling.js")
async def proxy_background_polling():
    """Proxy background-polling.js from Node.js backend"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:3001/background-polling.js")
        return Response(content=response.content, media_type="application/javascript")

@app.get("/global-scan-indicator.js")
async def proxy_global_scan_indicator():
    """Proxy global-scan-indicator.js from Node.js backend"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:3001/global-scan-indicator.js")
        return Response(content=response.content, media_type="application/javascript")

@app.get("/sidebar-admin-control.js")
async def proxy_sidebar_admin_control():
    """Proxy sidebar-admin-control.js from Node.js backend"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:3001/sidebar-admin-control.js")
        return Response(content=response.content, media_type="application/javascript")

# =========================
# Page routes
# =========================
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/index.html", {"request": request, "user": user})

@app.get("/active-raffle", response_class=HTMLResponse)
async def active_raffle(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    page = TEMPLATES_DIR / "pages" / "active_raffle.html"
    if not page.exists():
        return HTMLResponse("<h1>active_raffle.html not found</h1>", status_code=404)
    return templates.TemplateResponse("pages/active_raffle.html", {"request": request, "user": user})

@app.get("/raffle-history", response_class=HTMLResponse)
async def raffle_history(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    page = TEMPLATES_DIR / "pages" / "raffle_history.html"
    if not page.exists():
        return HTMLResponse("<h1>raffle_history.html not found</h1>", status_code=404)
    return templates.TemplateResponse("pages/raffle_history.html", {"request": request, "user": user})
@app.get("/activity-log", response_class=HTMLResponse)
async def activity_log(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    page = TEMPLATES_DIR / "pages" / "activity_log.html"
    if not page.exists():
        return HTMLResponse("<h1>activity_log.html not found</h1>", status_code=404)
    return templates.TemplateResponse("pages/activity_log.html", {"request": request, "user": user})
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    page = TEMPLATES_DIR / "pages" / "profile.html"
    if not page.exists():
        return HTMLResponse("<h1>profile.html not found</h1>", status_code=404)
    return templates.TemplateResponse("pages/profile.html", {"request": request, "user": user})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    page = TEMPLATES_DIR / "pages" / "settings.html"
    if not page.exists():
        return HTMLResponse("<h1>settings.html not found</h1>", status_code=404)
    return templates.TemplateResponse("pages/settings.html", {"request": request, "user": user})

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    """Help & Guides page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    page = TEMPLATES_DIR / "pages" / "help.html"
    if not page.exists():
        return HTMLResponse("<h1>help.html not found</h1><p>Create: app/templates/pages/help.html</p>", status_code=404)

    return templates.TemplateResponse("pages/help.html", {"request": request, "user": user})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin dashboard page - requires admin privileges"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Always render the page - let JavaScript handle access control with modal
    page = TEMPLATES_DIR / "pages" / "admin.html"
    if not page.exists():
        return HTMLResponse("<h1>admin.html not found</h1><p>Create: app/templates/pages/admin.html</p>", status_code=404)

    return templates.TemplateResponse("pages/admin.html", {"request": request, "user": user})

@app.get("/master-tracker", response_class=HTMLResponse)
async def master_tracker_page(request: Request):
    """Master Raffle Tracker page - requires admin privileges"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Always render the page - let JavaScript handle access control with modal
    page = TEMPLATES_DIR / "pages" / "master-tracker.html"
    if not page.exists():
        return HTMLResponse("<h1>master-tracker.html not found</h1><p>Create: app/templates/pages/master-tracker.html</p>", status_code=404)

    return templates.TemplateResponse("pages/master-tracker.html", {"request": request, "user": user})

@app.get("/user-management", response_class=HTMLResponse)
async def user_management_page(request: Request):
    """User management page - requires admin privileges"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Always render the page - let JavaScript handle access control with modal
    page = TEMPLATES_DIR / "pages" / "user_management.html"
    if not page.exists():
        return HTMLResponse("<h1>user_management.html not found</h1><p>Create: app/templates/pages/user_management.html</p>", status_code=404)

    return templates.TemplateResponse("pages/user_management.html", {"request": request, "user": user})

@app.get("/raffle-monitor", response_class=HTMLResponse)
async def raffle_monitor_page(request: Request):
    """Raffle monitor page - requires admin privileges"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Always render the page - let JavaScript handle access control with modal
    page = TEMPLATES_DIR / "pages" / "raffle_monitor.html"
    if not page.exists():
        return HTMLResponse("<h1>raffle_monitor.html not found</h1><p>Create: app/templates/pages/raffle_monitor.html</p>", status_code=404)

    return templates.TemplateResponse("pages/raffle_monitor.html", {"request": request, "user": user})

@app.get("/discord", response_class=HTMLResponse)
async def discord_page(request: Request):
    """Discord servers page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    page = TEMPLATES_DIR / "pages" / "discord.html"
    if not page.exists():
        return HTMLResponse("<h1>discord.html not found</h1><p>Create: app/templates/pages/discord.html</p>", status_code=404)

    return templates.TemplateResponse("pages/discord.html", {"request": request, "user": user})

@app.get("/donate", response_class=HTMLResponse)
async def donate_page(request: Request):
    """Donate/Support page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    page = TEMPLATES_DIR / "pages" / "donate.html"
    if not page.exists():
        return HTMLResponse("<h1>donate.html not found</h1><p>Create: app/templates/pages/donate.html</p>", status_code=404)
    return templates.TemplateResponse("pages/donate.html", {"request": request, "user": user})

# =========================
# HTML FILE ALIASES (for Electron app direct file requests)
# =========================

@app.get("/active_raffle.html", response_class=HTMLResponse)
async def active_raffle_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/active_raffle.html", {"request": request, "user": user})

@app.get("/raffle_history.html", response_class=HTMLResponse)
async def raffle_history_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/raffle_history.html", {"request": request, "user": user})

@app.get("/activity_log.html", response_class=HTMLResponse)
async def activity_log_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/activity_log.html", {"request": request, "user": user})

@app.get("/profile.html", response_class=HTMLResponse)
async def profile_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/profile.html", {"request": request, "user": user})

@app.get("/settings.html", response_class=HTMLResponse)
async def settings_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/settings.html", {"request": request, "user": user})

@app.get("/help.html", response_class=HTMLResponse)
async def help_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/help.html", {"request": request, "user": user})

@app.get("/admin.html", response_class=HTMLResponse)
async def admin_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    # Always render the page - let JavaScript handle access control with modal
    return templates.TemplateResponse("pages/admin.html", {"request": request, "user": user})

@app.get("/user_management.html", response_class=HTMLResponse)
async def user_management_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    # Always render the page - let JavaScript handle access control with modal
    return templates.TemplateResponse("pages/user_management.html", {"request": request, "user": user})

@app.get("/raffle_monitor.html", response_class=HTMLResponse)
async def raffle_monitor_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    # Always render the page - let JavaScript handle access control with modal
    return templates.TemplateResponse("pages/raffle_monitor.html", {"request": request, "user": user})

@app.get("/discord.html", response_class=HTMLResponse)
async def discord_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/discord.html", {"request": request, "user": user})

@app.get("/donate.html", response_class=HTMLResponse)
async def donate_html(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("pages/donate.html", {"request": request, "user": user})


# =========================
# Existing image processing route (kept)
# =========================
@app.get("/process-image")
async def process_image():
    try:
        if not SOURCE_IMG.exists():
            return JSONResponse({"ok": False, "error": f"Source image not found: {SOURCE_IMG}"}, status_code=404)

        img = Image.open(SOURCE_IMG)
        img = img.convert("L")
        img = img.resize((250, 700))

        OUTPUT_IMG.parent.mkdir(parents=True, exist_ok=True)
        img.save(OUTPUT_IMG)

        return {"ok": True, "output": "/static/processed/sidebar_processed.png"}

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# =========================
# Include Database API Routes
# =========================
