import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from config import DB_PATH


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            operation_date TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            business_unit TEXT,
            category TEXT,
            amount REAL NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0,
            event_name TEXT,
            customer TEXT,
            people INTEGER,
            reservation_status TEXT,
            payment_method TEXT,
            notes TEXT,
            telegram_user_id INTEGER,
            telegram_username TEXT
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_operations_date
        ON operations(operation_date)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_operations_event
        ON operations(event_name)
        """)


def insert_operation(data: dict[str, Any], user_id: int, username: str | None) -> int:
    with connect() as conn:
        cur = conn.execute("""
        INSERT INTO operations (
            created_at, operation_date, operation_type, business_unit, category,
            amount, cost, event_name, customer, people, reservation_status,
            payment_method, notes, telegram_user_id, telegram_username
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            data.get("operation_date") or date.today().isoformat(),
            data.get("operation_type") or "otro",
            data.get("business_unit"),
            data.get("category"),
            float(data.get("amount") or 0),
            float(data.get("cost") or 0),
            data.get("event_name"),
            data.get("customer"),
            data.get("people"),
            data.get("reservation_status"),
            data.get("payment_method"),
            data.get("notes"),
            user_id,
            username,
        ))
        return cur.lastrowid


def _where(filters: dict[str, Any]):
    clauses = []
    params: list[Any] = []

    if filters.get("business_unit"):
        clauses.append("LOWER(business_unit) = LOWER(?)")
        params.append(filters["business_unit"])

    if filters.get("event_name"):
        clauses.append("LOWER(COALESCE(event_name,'')) LIKE LOWER(?)")
        params.append(f"%{filters['event_name']}%")

    if filters.get("category"):
        clauses.append("LOWER(COALESCE(category,'')) LIKE LOWER(?)")
        params.append(f"%{filters['category']}%")

    if filters.get("date_from"):
        clauses.append("operation_date >= ?")
        params.append(filters["date_from"])

    if filters.get("date_to"):
        clauses.append("operation_date <= ?")
        params.append(filters["date_to"])

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def aggregate(filters: dict[str, Any]) -> dict[str, Any]:
    where_sql, params = _where(filters)
    with connect() as conn:
        row = conn.execute(f"""
        SELECT
            COUNT(*) AS records,
            COALESCE(SUM(CASE WHEN operation_type IN ('venta','cobro','ingreso','evento')
                              THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN operation_type IN ('compra','gasto','devolucion')
                              THEN amount ELSE 0 END), 0) AS outflows,
            COALESCE(SUM(cost), 0) AS explicit_costs,
            COALESCE(SUM(CASE WHEN operation_type = 'reserva' THEN 1 ELSE 0 END), 0) AS reservations,
            COALESCE(SUM(CASE WHEN operation_type = 'reserva'
                               AND LOWER(COALESCE(reservation_status,'')) IN ('confirmada','confirmado')
                              THEN 1 ELSE 0 END), 0) AS confirmed_reservations
        FROM operations
        {where_sql}
        """, params).fetchone()

        result = dict(row)
        result["total_costs"] = float(result["outflows"]) + float(result["explicit_costs"])
        result["profit"] = float(result["income"]) - result["total_costs"]
        result["margin_pct"] = (
            (result["profit"] / float(result["income"])) * 100
            if float(result["income"]) else None
        )
        return result


def recent_operations(limit: int = 10):
    with connect() as conn:
        return conn.execute("""
        SELECT * FROM operations
        ORDER BY id DESC
        LIMIT ?
        """, (limit,)).fetchall()


def seed_demo(user_id: int, username: str | None):
    demo = [
        {
            "operation_date": date.today().isoformat(),
            "operation_type": "venta",
            "business_unit": "bar",
            "category": "ventas",
            "amount": 685000,
            "notes": "Ventas de ejemplo del bar",
        },
        {
            "operation_date": date.today().isoformat(),
            "operation_type": "evento",
            "business_unit": "catering",
            "category": "evento",
            "amount": 850000,
            "cost": 510000,
            "event_name": "López",
            "customer": "López",
            "notes": "Evento de demostración",
        },
        {
            "operation_date": date.today().isoformat(),
            "operation_type": "reserva",
            "business_unit": "salon",
            "amount": 120000,
            "customer": "Juan Pérez",
            "people": 8,
            "reservation_status": "confirmada",
            "notes": "Seña de reserva",
        },
    ]
    ids = [insert_operation(x, user_id, username) for x in demo]
    return ids
