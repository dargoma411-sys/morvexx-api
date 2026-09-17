from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime

app = FastAPI()

# Разрешаем запросы откуда угодно (чтобы Mini App мог общаться)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# База данных
conn = sqlite3.connect('morvexx_shop.db', check_same_thread=False)
cursor = conn.cursor()

# Создаём таблицу заказов (если её ещё нет)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        category TEXT,
        quantity INTEGER,
        unit TEXT,
        price REAL,
        currency TEXT,
        created_at TEXT
    )
''')
conn.commit()

# Категории (те же, что в боте)
CATEGORIES = {
    "cat_stars": {"name": "⭐ Telegram Stars", "min": 100, "max": 100000, "unit": "звёзд", "rate": 1.45},
    "cat_robux": {"name": "🎮 Robux", "min": 100, "max": 1000000, "unit": "Robux", "rate": 1.1},
    "cat_steam": {"name": "💨 Steam Balance", "min": 1, "max": 10000, "unit": "баланса", "rate": 1.05},
    "cat_standoff": {"name": "🔫 Standoff 2 Gold", "min": 100, "max": 1000000, "unit": "голды", "rate": 0.5},
    "cat_brawl": {"name": "💎 Brawl Stars Gems", "min": 100, "max": 10000, "unit": "гемов", "rate": 1.2},
}

# Форматирование чисел
def format_number(n) -> str:
    if isinstance(n, float):
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{n:,}".replace(",", ".")

# 1. Получить список категорий
@app.get("/api/categories")
async def get_categories():
    return CATEGORIES

# 2. Создать заказ
@app.post("/api/orders")
async def create_order(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    username = data.get("username")
    category = data.get("category")
    quantity = data.get("quantity")

    cat = CATEGORIES.get(category)
    if not cat:
        return {"error": "Категория не найдена"}

    if quantity < cat["min"] or quantity > cat["max"]:
        return {"error": f"Количество от {cat['min']} до {cat['max']}"}

    price = quantity * cat["rate"]

    cursor.execute(
        "INSERT INTO orders (user_id, username, category, quantity, unit, price, currency, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, category, quantity, cat["unit"], price, None, datetime.now().isoformat())
    )
    conn.commit()

    return {
        "success": True,
        "order_id": cursor.lastrowid,
        "price": round(price, 2),
        "price_text": format_number(round(price, 2)),
    }

# 3. Получить заказы пользователя
@app.get("/api/orders/{user_id}")
async def get_orders(user_id: int):
    cursor.execute(
        "SELECT id, category, quantity, unit, price FROM orders WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    )
    orders = cursor.fetchall()
    result = []
    for oid, cat, qty, unit, price in orders:
        result.append({
            "id": oid,
            "category": cat,
            "category_name": CATEGORIES[cat]["name"],
            "quantity": qty,
            "unit": unit,
            "price": round(price, 2),
            "price_text": format_number(round(price, 2)),
        })
    return result

# 4. Профиль
@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int):
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM orders WHERE user_id=?", (user_id,))
    count, total = cursor.fetchone()
    return {
        "orders_count": count,
        "total_spent": round(total, 2),
        "total_spent_text": format_number(round(total, 2)),
    }
