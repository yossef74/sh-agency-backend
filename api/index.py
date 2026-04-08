from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime
import sqlite3, secrets, os, httpx
from pathlib import Path

app = FastAPI(title="SH Agency API")

# ── CORS ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج: ضع دومين الموقع بالظبط
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

# ── CONFIG (من Environment Variables) ─────────────────
ADMIN_USER     = os.getenv("ADMIN_USER", "shimyAdmin")
ADMIN_PASS     = os.getenv("ADMIN_PASS", "sh@agency2026!")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")        # من resend.com
NOTIFY_EMAIL   = os.getenv("NOTIFY_EMAIL", "")          # الإيميل اللي هيستقبل الإشعارات

# ── DATABASE ──────────────────────────────────────────
DB_PATH = Path("/tmp/sh_agency.db")   # Vercel بيستخدم /tmp

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            email     TEXT    NOT NULL,
            company   TEXT,
            message   TEXT    NOT NULL,
            is_read   INTEGER DEFAULT 0,
            created_at TEXT   DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            description TEXT,
            image_url   TEXT,
            project_url TEXT,
            tags        TEXT,
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    # بيانات Portfolio أولية لو الجدول فاضي
    c.execute("SELECT COUNT(*) FROM portfolio")
    if c.fetchone()[0] == 0:
        sample = [
            ("NovaTech Rebrand",    "Branding",       "Complete brand overhaul for a SaaS startup", "https://placehold.co/600x400/bc13fe/fff?text=NovaTech",    "#",  "Branding, Logo, Identity"),
            ("PulseApp UI/UX",      "UI/UX Design",   "Mobile app design for health tracking",       "https://placehold.co/600x400/00e0ff/000?text=PulseApp",    "#",  "Figma, Mobile, UX"),
            ("OrbitMedia Campaign", "Social Media",   "Growth campaign — 300% reach in 60 days",     "https://placehold.co/600x400/ff3c6e/fff?text=OrbitMedia",  "#",  "Meta Ads, Content"),
            ("VaultX Web Platform", "Web Development","Full-stack platform for crypto analytics",     "https://placehold.co/600x400/7800c8/fff?text=VaultX",      "#",  "React, FastAPI, Web3"),
        ]
        c.executemany(
            "INSERT INTO portfolio (title,category,description,image_url,project_url,tags) VALUES (?,?,?,?,?,?)",
            sample
        )
    conn.commit()
    conn.close()

init_db()

# ── AUTH ──────────────────────────────────────────────
def require_admin(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username.encode(), ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(creds.password.encode(), ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username

# ── EMAIL (Resend) ────────────────────────────────────
async def send_notification(name: str, email: str, company: str, message: str):
    if not RESEND_API_KEY or not NOTIFY_EMAIL:
        return  # إذا مفيش مفاتيح، بس حفظ في DB
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from":    "SH Agency <onboarding@resend.dev>",
                "to":      [NOTIFY_EMAIL],
                "subject": f"🚀 New Lead: {name} — {company or 'No Company'}",
                "html":    f"""
                <div style="font-family:sans-serif;max-width:600px;margin:auto;background:#0a0a15;color:#f0f0ff;padding:32px;border-radius:12px;border:1px solid #bc13fe44">
                    <h2 style="color:#bc13fe;margin:0 0 24px">New Contact from SH Agency</h2>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> <a href="mailto:{email}" style="color:#00e0ff">{email}</a></p>
                    <p><strong>Company:</strong> {company or '—'}</p>
                    <hr style="border-color:#ffffff11;margin:20px 0">
                    <p><strong>Message:</strong></p>
                    <p style="background:#ffffff08;padding:16px;border-radius:8px;border-left:3px solid #bc13fe">{message}</p>
                    <p style="color:#6b7280;font-size:12px;margin-top:24px">Sent via SH Agency Contact Form</p>
                </div>"""
            }
        )

# ══════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════

class ContactForm(BaseModel):
    name:    str
    email:   str
    company: str = ""
    message: str

@app.post("/api/contact", status_code=201)
async def submit_contact(form: ContactForm, db: sqlite3.Connection = Depends(get_db)):
    if len(form.name) < 2 or len(form.message) < 10:
        raise HTTPException(400, "Name or message too short")
    db.execute(
        "INSERT INTO messages (name,email,company,message) VALUES (?,?,?,?)",
        (form.name.strip(), form.email.strip(), form.company.strip(), form.message.strip())
    )
    db.commit()
    await send_notification(form.name, form.email, form.company, form.message)
    return {"success": True, "message": "Message received! We'll get back to you soon 🚀"}


@app.get("/api/portfolio")
def get_portfolio(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM portfolio WHERE is_active=1 ORDER BY id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
# ADMIN ENDPOINTS  (محمية بباسورد)
# ══════════════════════════════════════════════════════

# ── Messages ──────────────────────────────────────────
@app.get("/api/admin/messages")
def admin_get_messages(db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    rows = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

@app.patch("/api/admin/messages/{msg_id}/read")
def mark_read(msg_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    db.execute("UPDATE messages SET is_read=1 WHERE id=?", (msg_id,))
    db.commit()
    return {"success": True}

@app.delete("/api/admin/messages/{msg_id}")
def delete_message(msg_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    db.execute("DELETE FROM messages WHERE id=?", (msg_id,))
    db.commit()
    return {"success": True}

# ── Portfolio ─────────────────────────────────────────
class ProjectItem(BaseModel):
    title:       str
    category:    str
    description: str = ""
    image_url:   str = ""
    project_url: str = ""
    tags:        str = ""

@app.post("/api/admin/portfolio", status_code=201)
def add_project(item: ProjectItem, db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    db.execute(
        "INSERT INTO portfolio (title,category,description,image_url,project_url,tags) VALUES (?,?,?,?,?,?)",
        (item.title, item.category, item.description, item.image_url, item.project_url, item.tags)
    )
    db.commit()
    return {"success": True}

@app.delete("/api/admin/portfolio/{project_id}")
def delete_project(project_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    db.execute("UPDATE portfolio SET is_active=0 WHERE id=?", (project_id,))
    db.commit()
    return {"success": True}

@app.put("/api/admin/portfolio/{project_id}")
def update_project(project_id: int, item: ProjectItem, db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    db.execute(
        "UPDATE portfolio SET title=?,category=?,description=?,image_url=?,project_url=?,tags=? WHERE id=?",
        (item.title, item.category, item.description, item.image_url, item.project_url, item.tags, project_id)
    )
    db.commit()
    return {"success": True}

# ── Stats ─────────────────────────────────────────────
@app.get("/api/admin/stats")
def admin_stats(db: sqlite3.Connection = Depends(get_db), _=Depends(require_admin)):
    total_msg   = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    unread_msg  = db.execute("SELECT COUNT(*) FROM messages WHERE is_read=0").fetchone()[0]
    total_proj  = db.execute("SELECT COUNT(*) FROM portfolio WHERE is_active=1").fetchone()[0]
    return {"total_messages": total_msg, "unread_messages": unread_msg, "total_projects": total_proj}

# ── Health ────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
