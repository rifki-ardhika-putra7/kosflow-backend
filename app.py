import libsql_experimental as sqlite3  # <-- Pengganti sqlite3 bawaan
import uuid
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="KosFlow API", version="2.0")

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════════════
# DATABASE SETUP (TURSO CLOUD)
# ══════════════════════════════════════════════════════════════════

# Masukkan URL dan Token kamu di antara tanda kutip
TURSO_URL = "libsql://kosflow-rifki-ardhika-putra7.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODAxNjQzMjksImlkIjoiMDE5ZTdhMGMtMzgwMS03OGM4LWE2ZmMtNTIzYjYzMDUzYzNmIiwicmlkIjoiODk3YzViOTUtNDc4Yi00OGFhLWIyZmMtNDEzZWM3YjhkMzYzIn0.ay-etYRqKXdPjc2cEmQ8I2jWxGHV44zXk_yWCP0eyg1TQ1E5dJ2tqWgdZxdLnvt325uf8gNN3SHtdO1VTNk0Cw"

def get_db():
    # Koneksi langsung ke cloud Turso
    conn = sqlite3.connect(TURSO_URL, auth_token=TURSO_TOKEN)
    
    # Custom format supaya hasilnya tetap bisa dibaca sebagai Dictionary oleh FastAPI
    def dict_factory(cursor, row):
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}
        
    conn.row_factory = dict_factory
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── users ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            weekly_budget REAL DEFAULT 300000,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── expenses ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            note        TEXT DEFAULT '',
            date        TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── category budgets ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS category_budgets (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            category    TEXT NOT NULL,
            amount      REAL DEFAULT 0,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── inventory ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            item_id     TEXT NOT NULL,
            emoji       TEXT DEFAULT '📦',
            name        TEXT NOT NULL,
            qty         REAL DEFAULT 0,
            unit        TEXT DEFAULT 'pcs',
            daily_use   REAL DEFAULT 1,
            threshold   REAL DEFAULT 1,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── tasks ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            text        TEXT NOT NULL,
            due_date    TEXT DEFAULT '',
            priority    TEXT DEFAULT 'medium',
            done        INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── habits ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            habit_id    TEXT NOT NULL,
            emoji       TEXT DEFAULT '⭐',
            name        TEXT NOT NULL,
            color       TEXT DEFAULT 'green',
            sort_order  INTEGER DEFAULT 0,
            UNIQUE(user_id, habit_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── habit_logs ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS habit_logs (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            habit_id    TEXT NOT NULL,
            log_date    TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, habit_id, log_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

init_db()

# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def new_id():
    return str(uuid.uuid4())[:12]

def today_str():
    return date.today().isoformat()

def row_to_dict(row):
    return dict(row) if row else None

DEFAULT_FOOD = [
    {"item_id": "rice",    "emoji": "🌾", "name": "Rice",         "qty": 5,  "unit": "kg",   "daily_use": 0.3,  "threshold": 1},
    {"item_id": "eggs",    "emoji": "🥚", "name": "Eggs",         "qty": 12, "unit": "pcs",  "daily_use": 2,    "threshold": 4},
    {"item_id": "noodles", "emoji": "🍜", "name": "Noodles",      "qty": 8,  "unit": "pcs",  "daily_use": 1.5,  "threshold": 3},
    {"item_id": "water",   "emoji": "💧", "name": "Gallon Water", "qty": 2,  "unit": "gal",  "daily_use": 0.3,  "threshold": 1},
    {"item_id": "oil",     "emoji": "🫙", "name": "Cooking Oil",  "qty": 1,  "unit": "L",    "daily_use": 0.05, "threshold": 0.2},
    {"item_id": "coffee",  "emoji": "☕", "name": "Coffee",       "qty": 15, "unit": "sach", "daily_use": 2,    "threshold": 5},
    {"item_id": "bread",   "emoji": "🍞", "name": "Bread",        "qty": 1,  "unit": "pcs",  "daily_use": 0.5,  "threshold": 1},
    {"item_id": "salt",    "emoji": "🧂", "name": "Salt",         "qty": 1,  "unit": "kg",   "daily_use": 0.01, "threshold": 0.1},
]

DEFAULT_HABITS = [
    {"habit_id": "workout", "emoji": "🏋️", "name": "Workout",    "color": "green",  "sort_order": 0},
    {"habit_id": "study",   "emoji": "📚", "name": "Study",       "color": "blue",   "sort_order": 1},
    {"habit_id": "sleep",   "emoji": "😴", "name": "Sleep Early", "color": "purple", "sort_order": 2},
    {"habit_id": "saving",  "emoji": "💰", "name": "Save Money",  "color": "yellow", "sort_order": 3},
    {"habit_id": "water",   "emoji": "💧", "name": "Drink Water", "color": "teal",   "sort_order": 4},
    {"habit_id": "noJunk",  "emoji": "🥗", "name": "Eat Healthy", "color": "orange", "sort_order": 5},
]

DEFAULT_CAT_BUDGETS = {
    "food": 120000, "transport": 50000, "campus": 40000,
    "shopping": 40000, "entertainment": 30000, "emergency": 20000
}

def seed_user_defaults(conn, user_id):
    """Seed inventory, habits, and category budgets for a new user."""
    for item in DEFAULT_FOOD:
        conn.execute(
            "INSERT OR IGNORE INTO inventory (id, user_id, item_id, emoji, name, qty, unit, daily_use, threshold) VALUES (?,?,?,?,?,?,?,?,?)",
            (new_id(), user_id, item["item_id"], item["emoji"], item["name"], item["qty"], item["unit"], item["daily_use"], item["threshold"])
        )
    for h in DEFAULT_HABITS:
        conn.execute(
            "INSERT OR IGNORE INTO habits (id, user_id, habit_id, emoji, name, color, sort_order) VALUES (?,?,?,?,?,?,?)",
            (new_id(), user_id, h["habit_id"], h["emoji"], h["name"], h["color"], h["sort_order"])
        )
    for cat, amt in DEFAULT_CAT_BUDGETS.items():
        conn.execute(
            "INSERT OR IGNORE INTO category_budgets (id, user_id, category, amount) VALUES (?,?,?,?)",
            (new_id(), user_id, cat, amt)
        )
    conn.commit()

# ══════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    name: str
    weekly_budget: Optional[float] = 300000

class UserUpdate(BaseModel):
    name: Optional[str] = None
    weekly_budget: Optional[float] = None

class ExpenseCreate(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    date: Optional[str] = None

class BudgetUpdate(BaseModel):
    weekly_budget: Optional[float] = None
    categories: Optional[dict] = None

class InventoryAdjust(BaseModel):
    qty: Optional[float] = None     # set absolute value
    delta: Optional[float] = None   # adjust relative

class TaskCreate(BaseModel):
    text: str
    due_date: Optional[str] = ""
    priority: Optional[str] = "medium"

class TaskUpdate(BaseModel):
    done: Optional[bool] = None
    text: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None

class HabitCreate(BaseModel):
    habit_id: str
    emoji: Optional[str] = "⭐"
    name: str
    color: Optional[str] = "green"

class HabitLogToggle(BaseModel):
    log_date: Optional[str] = None  # defaults to today

# ══════════════════════════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"message": "KosFlow API v2.0 🏠", "status": "running", "docs": "/docs"}

# ══════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users")
def get_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/users", status_code=201)
def create_user(body: UserCreate):
    user_id = new_id()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (id, name, weekly_budget) VALUES (?, ?, ?)",
            (user_id, body.name.strip(), body.weekly_budget)
        )
        conn.commit()
        seed_user_defaults(conn, user_id)
        user = dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        return {"success": True, "user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)

@app.patch("/api/users/{user_id}")
def update_user(user_id: str, body: UserUpdate):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    updates, vals = [], []
    if body.name is not None:
        updates.append("name=?"); vals.append(body.name.strip())
    if body.weekly_budget is not None:
        updates.append("weekly_budget=?"); vals.append(body.weekly_budget)
    if updates:
        updates.append("updated_at=CURRENT_TIMESTAMP")
        vals.append(user_id)
        conn.execute(f"UPDATE users SET {','.join(updates)} WHERE id=?", vals)
        conn.commit()
    row = dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
    conn.close()
    return {"success": True, "user": row}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: str):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "User deleted"}

# ══════════════════════════════════════════════════════════════════
# EXPENSES
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/expenses")
def get_expenses(user_id: str, filter: Optional[str] = "all"):
    conn = get_db()
    if filter == "today":
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id=? AND date=? ORDER BY created_at DESC",
            (user_id, today_str())
        ).fetchall()
    elif filter == "week":
        # Monday of this week
        from datetime import timedelta
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id=? AND date>=? ORDER BY date DESC",
            (user_id, monday.isoformat())
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC, created_at DESC",
            (user_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/users/{user_id}/expenses", status_code=201)
def add_expense(user_id: str, body: ExpenseCreate):
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    exp_id = new_id()
    exp_date = body.date or today_str()
    conn.execute(
        "INSERT INTO expenses (id, user_id, amount, category, note, date) VALUES (?,?,?,?,?,?)",
        (exp_id, user_id, body.amount, body.category, body.note or "", exp_date)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM expenses WHERE id=?", (exp_id,)).fetchone())
    conn.close()
    return {"success": True, "expense": row}

@app.delete("/api/users/{user_id}/expenses/{exp_id}")
def delete_expense(user_id: str, exp_id: str):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (exp_id, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Expense deleted"}

# ══════════════════════════════════════════════════════════════════
# BUDGETS
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/budget")
def get_budget(user_id: str):
    conn = get_db()
    user = conn.execute("SELECT weekly_budget FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    cat_rows = conn.execute(
        "SELECT category, amount FROM category_budgets WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return {
        "weekly": user["weekly_budget"],
        "categories": {r["category"]: r["amount"] for r in cat_rows}
    }

@app.patch("/api/users/{user_id}/budget")
def update_budget(user_id: str, body: BudgetUpdate):
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    if body.weekly_budget is not None:
        conn.execute(
            "UPDATE users SET weekly_budget=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (body.weekly_budget, user_id)
        )
    if body.categories:
        for cat, amt in body.categories.items():
            conn.execute(
                "INSERT INTO category_budgets (id, user_id, category, amount) VALUES (?,?,?,?) "
                "ON CONFLICT(user_id, category) DO UPDATE SET amount=excluded.amount, updated_at=CURRENT_TIMESTAMP",
                (new_id(), user_id, cat, float(amt))
            )
    conn.commit()
    conn.close()
    return {"success": True, "message": "Budget updated"}

# ══════════════════════════════════════════════════════════════════
# INVENTORY
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/inventory")
def get_inventory(user_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? ORDER BY name ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.patch("/api/users/{user_id}/inventory/{item_id}")
def update_inventory_item(user_id: str, item_id: str, body: InventoryAdjust):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
    current_qty = row["qty"]
    if body.qty is not None:
        new_qty = max(0, body.qty)
    elif body.delta is not None:
        new_qty = max(0, round(current_qty + body.delta, 3))
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Provide qty or delta")
    conn.execute(
        "UPDATE inventory SET qty=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND item_id=?",
        (new_qty, user_id, item_id)
    )
    conn.commit()
    updated = dict(conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id)
    ).fetchone())
    conn.close()
    return {"success": True, "item": updated}

# ══════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/tasks")
def get_tasks(user_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY done ASC, created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["done"] = bool(d["done"])
        result.append(d)
    return result

@app.post("/api/users/{user_id}/tasks", status_code=201)
def add_task(user_id: str, body: TaskCreate):
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    task_id = new_id()
    conn.execute(
        "INSERT INTO tasks (id, user_id, text, due_date, priority) VALUES (?,?,?,?,?)",
        (task_id, user_id, body.text, body.due_date or "", body.priority)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    row["done"] = bool(row["done"])
    conn.close()
    return {"success": True, "task": row}

@app.patch("/api/users/{user_id}/tasks/{task_id}")
def update_task(user_id: str, task_id: str, body: TaskUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    updates, vals = [], []
    if body.done is not None:
        updates.append("done=?"); vals.append(1 if body.done else 0)
    if body.text is not None:
        updates.append("text=?"); vals.append(body.text)
    if body.due_date is not None:
        updates.append("due_date=?"); vals.append(body.due_date)
    if body.priority is not None:
        updates.append("priority=?"); vals.append(body.priority)
    if updates:
        vals += [task_id, user_id]
        conn.execute(f"UPDATE tasks SET {','.join(updates)} WHERE id=? AND user_id=?", vals)
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    updated["done"] = bool(updated["done"])
    conn.close()
    return {"success": True, "task": updated}

@app.delete("/api/users/{user_id}/tasks/{task_id}")
def delete_task(user_id: str, task_id: str):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Task deleted"}

# ══════════════════════════════════════════════════════════════════
# HABITS
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/habits")
def get_habits(user_id: str):
    conn = get_db()
    habits = conn.execute(
        "SELECT * FROM habits WHERE user_id=? ORDER BY sort_order ASC, name ASC", (user_id,)
    ).fetchall()
    # For each habit, get logs for last 30 days
    result = []
    for h in habits:
        hd = dict(h)
        logs = conn.execute(
            "SELECT log_date FROM habit_logs WHERE user_id=? AND habit_id=? ORDER BY log_date DESC LIMIT 30",
            (user_id, h["habit_id"])
        ).fetchall()
        hd["logs"] = [r["log_date"] for r in logs]
        result.append(hd)
    conn.close()
    return result

@app.get("/api/users/{user_id}/habits/logs")
def get_habit_logs(user_id: str, days: int = 7):
    """Return all logs for the user for the past N days."""
    conn = get_db()
    from datetime import timedelta
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT habit_id, log_date FROM habit_logs WHERE user_id=? AND log_date>=? ORDER BY log_date DESC",
        (user_id, since)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/users/{user_id}/habits/{habit_id}/toggle")
def toggle_habit(user_id: str, habit_id: str, body: HabitLogToggle = HabitLogToggle()):
    conn = get_db()
    log_date = body.log_date or today_str()
    existing = conn.execute(
        "SELECT id FROM habit_logs WHERE user_id=? AND habit_id=? AND log_date=?",
        (user_id, habit_id, log_date)
    ).fetchone()
    if existing:
        conn.execute(
            "DELETE FROM habit_logs WHERE user_id=? AND habit_id=? AND log_date=?",
            (user_id, habit_id, log_date)
        )
        done = False
    else:
        conn.execute(
            "INSERT INTO habit_logs (id, user_id, habit_id, log_date) VALUES (?,?,?,?)",
            (new_id(), user_id, habit_id, log_date)
        )
        done = True
    conn.commit()
    conn.close()
    return {"success": True, "done": done, "log_date": log_date}

# ══════════════════════════════════════════════════════════════════
# STATS / SUMMARY
# ══════════════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/summary")
def get_summary(user_id: str):
    """Return aggregate stats for the dashboard in one call."""
    from datetime import timedelta
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    today = today_str()
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    today_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE user_id=? AND date=?",
        (user_id, today)
    ).fetchone()["total"]

    week_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE user_id=? AND date>=?",
        (user_id, monday)
    ).fetchone()["total"]

    pending_tasks = conn.execute(
        "SELECT COUNT(*) as cnt FROM tasks WHERE user_id=? AND done=0", (user_id,)
    ).fetchone()["cnt"]

    total_habits = conn.execute(
        "SELECT COUNT(*) as cnt FROM habits WHERE user_id=?", (user_id,)
    ).fetchone()["cnt"]

    done_habits_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM habit_logs WHERE user_id=? AND log_date=?",
        (user_id, today)
    ).fetchone()["cnt"]

    low_stock = conn.execute(
        "SELECT COUNT(*) as cnt FROM inventory WHERE user_id=? AND qty > 0 AND qty <= threshold",
        (user_id,)
    ).fetchone()["cnt"]

    out_of_stock = conn.execute(
        "SELECT COUNT(*) as cnt FROM inventory WHERE user_id=? AND qty = 0", (user_id,)
    ).fetchone()["cnt"]

    conn.close()

    weekly_budget = user["weekly_budget"]
    remaining = weekly_budget - week_total
    pct_used = min(100, round((week_total / weekly_budget) * 100)) if weekly_budget > 0 else 0
    habit_pct = round((done_habits_today / total_habits) * 100) if total_habits > 0 else 0

    return {
        "user": dict(user),
        "today_total": today_total,
        "week_total": week_total,
        "remaining": remaining,
        "weekly_budget": weekly_budget,
        "pct_used": pct_used,
        "pending_tasks": pending_tasks,
        "habit_pct": habit_pct,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "is_emergency": remaining < (weekly_budget * 0.15),
        "is_warning": (remaining < (weekly_budget * 0.30)) and not (remaining < (weekly_budget * 0.15)),
    }

# ══════════════════════════════════════════════════════════════════
# LEGACY: expenses without user_id (backward compat, uses port 8001)
# ══════════════════════════════════════════════════════════════════

@app.get("/api/expenses")
def get_all_expenses_legacy():
    conn = get_db()
    rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC LIMIT 200").fetchall()
    conn.close()
    return [dict(r) for r in rows]