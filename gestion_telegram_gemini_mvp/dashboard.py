from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
import hmac
import secrets
from typing import Any

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from config import (
    COOKIE_SECURE,
    DASHBOARD_PASSWORD,
    DASHBOARD_PASSWORD_HASH,
    DASHBOARD_USERNAME,
    SECRET_KEY,
)
from database import connect, init_db

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)

INCOME_TYPES = {"venta", "cobro", "ingreso", "evento"}
OUTFLOW_TYPES = {"compra", "gasto", "devolucion"}


def money(value: float | int | None) -> str:
    value = float(value or 0)
    return f"${value:,.0f}".replace(",", ".")


def pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}%".replace(".", ",")


app.jinja_env.filters["money"] = money
app.jinja_env.filters["pct"] = pct


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_post_requests():
    if request.method != "POST":
        return None
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not submitted or not expected or not hmac.compare_digest(submitted, expected):
        abort(400, description="La sesión venció. Recargá la página e intentá nuevamente.")
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("dashboard_user"):
            next_url = request.full_path if request.query_string else request.path
            return redirect(url_for("login", next=next_url))
        return view(*args, **kwargs)

    return wrapped


def valid_next_url(value: str) -> bool:
    return value.startswith("/") and not value.startswith("//")


def password_is_valid(candidate: str) -> bool:
    if DASHBOARD_PASSWORD_HASH:
        return check_password_hash(DASHBOARD_PASSWORD_HASH, candidate)
    if DASHBOARD_PASSWORD:
        return hmac.compare_digest(DASHBOARD_PASSWORD.encode(), candidate.encode())
    return False


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("dashboard_user"):
        return redirect(url_for("dashboard"))

    configured = bool(DASHBOARD_PASSWORD_HASH or DASHBOARD_PASSWORD)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        username_ok = hmac.compare_digest(username.encode(), DASHBOARD_USERNAME.encode())
        if configured and username_ok and password_is_valid(password):
            session.clear()
            session.permanent = True
            session["dashboard_user"] = DASHBOARD_USERNAME
            session["csrf_token"] = secrets.token_urlsafe(32)
            destination = request.form.get("next", "")
            return redirect(destination if valid_next_url(destination) else url_for("dashboard"))
        flash("Usuario o contraseña incorrectos.", "error")

    return render_template(
        "login.html",
        configured=configured,
        next_url=request.values.get("next", ""),
    )


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/health")
def health():
    return jsonify(status="ok")


def query_filters() -> dict[str, str]:
    today = date.today()
    default_from = (today - timedelta(days=29)).isoformat()
    return {
        "date_from": request.args.get("date_from", default_from),
        "date_to": request.args.get("date_to", today.isoformat()),
        "business_unit": request.args.get("business_unit", "").strip().lower(),
        "operation_type": request.args.get("operation_type", "").strip().lower(),
        "q": request.args.get("q", "").strip(),
    }


def build_where(filters: dict[str, str]) -> tuple[str, list[Any]]:
    clauses = ["operation_date >= ?", "operation_date <= ?"]
    params: list[Any] = [filters["date_from"], filters["date_to"]]

    if filters["business_unit"]:
        clauses.append("LOWER(COALESCE(business_unit,'')) = ?")
        params.append(filters["business_unit"])
    if filters["operation_type"]:
        clauses.append("LOWER(operation_type) = ?")
        params.append(filters["operation_type"])
    if filters["q"]:
        term = f"%{filters['q']}%"
        clauses.append("(" 
            "LOWER(COALESCE(event_name,'')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(customer,'')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(category,'')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(notes,'')) LIKE LOWER(?)"
            ")")
        params.extend([term, term, term, term])

    return " WHERE " + " AND ".join(clauses), params


def metric_summary(where_sql: str, params: list[Any]) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(f"""
            SELECT
                COUNT(*) AS records,
                COALESCE(SUM(CASE WHEN operation_type IN ('venta','cobro','ingreso','evento') THEN amount ELSE 0 END),0) AS income,
                COALESCE(SUM(CASE WHEN operation_type IN ('compra','gasto','devolucion') THEN amount ELSE 0 END),0) AS outflows,
                COALESCE(SUM(cost),0) AS explicit_costs,
                COALESCE(SUM(CASE WHEN operation_type='reserva' THEN 1 ELSE 0 END),0) AS reservations,
                COALESCE(SUM(CASE WHEN operation_type='reserva' AND LOWER(COALESCE(reservation_status,'')) IN ('confirmada','confirmado') THEN 1 ELSE 0 END),0) AS confirmed_reservations
            FROM operations
            {where_sql}
        """, params).fetchone()
    d = dict(row)
    d["income"] = float(d["income"] or 0)
    d["costs"] = float(d["outflows"] or 0) + float(d["explicit_costs"] or 0)
    d["profit"] = d["income"] - d["costs"]
    d["margin_pct"] = (d["profit"] / d["income"] * 100) if d["income"] else None
    return d


def previous_period(filters: dict[str, str]) -> dict[str, Any]:
    start = datetime.fromisoformat(filters["date_from"]).date()
    end = datetime.fromisoformat(filters["date_to"]).date()
    days = max((end - start).days + 1, 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    prev_filters = dict(filters)
    prev_filters["date_from"] = prev_start.isoformat()
    prev_filters["date_to"] = prev_end.isoformat()
    where_sql, params = build_where(prev_filters)
    return metric_summary(where_sql, params)


def delta(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def daily_series(where_sql: str, params: list[Any]) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(f"""
            SELECT operation_date,
                   COALESCE(SUM(CASE WHEN operation_type IN ('venta','cobro','ingreso','evento') THEN amount ELSE 0 END),0) AS income,
                   COALESCE(SUM(CASE WHEN operation_type IN ('compra','gasto','devolucion') THEN amount ELSE 0 END),0) + COALESCE(SUM(cost),0) AS costs
            FROM operations
            {where_sql}
            GROUP BY operation_date
            ORDER BY operation_date ASC
        """, params).fetchall()
    return [dict(r) for r in rows]


def unit_performance(where_sql: str, params: list[Any]) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(f"""
            SELECT COALESCE(NULLIF(business_unit,''),'sin asignar') AS business_unit,
                   COALESCE(SUM(CASE WHEN operation_type IN ('venta','cobro','ingreso','evento') THEN amount ELSE 0 END),0) AS income,
                   COALESCE(SUM(CASE WHEN operation_type IN ('compra','gasto','devolucion') THEN amount ELSE 0 END),0) + COALESCE(SUM(cost),0) AS costs,
                   COUNT(*) AS records
            FROM operations
            {where_sql}
            GROUP BY COALESCE(NULLIF(business_unit,''),'sin asignar')
            ORDER BY income DESC
        """, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["profit"] = float(d["income"] or 0) - float(d["costs"] or 0)
        d["margin_pct"] = (d["profit"] / float(d["income"]) * 100) if d["income"] else None
        result.append(d)
    return result


def operations(where_sql: str, params: list[Any], limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(f"""
            SELECT * FROM operations
            {where_sql}
            ORDER BY operation_date DESC, id DESC
            LIMIT ?
        """, [*params, limit]).fetchall()
    return [dict(r) for r in rows]


def event_profitability(filters: dict[str, str]) -> list[dict[str, Any]]:
    clauses = ["operation_date >= ?", "operation_date <= ?", "COALESCE(event_name,'') <> ''"]
    params: list[Any] = [filters["date_from"], filters["date_to"]]
    if filters["business_unit"]:
        clauses.append("LOWER(COALESCE(business_unit,'')) = ?")
        params.append(filters["business_unit"])
    where = " WHERE " + " AND ".join(clauses)
    with connect() as conn:
        rows = conn.execute(f"""
            SELECT event_name,
                   MAX(customer) AS customer,
                   COALESCE(SUM(CASE WHEN operation_type IN ('venta','cobro','ingreso','evento') THEN amount ELSE 0 END),0) AS income,
                   COALESCE(SUM(CASE WHEN operation_type IN ('compra','gasto','devolucion') THEN amount ELSE 0 END),0) + COALESCE(SUM(cost),0) AS costs,
                   MAX(operation_date) AS operation_date
            FROM operations
            {where}
            GROUP BY event_name
            ORDER BY income DESC
            LIMIT 12
        """, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["profit"] = float(d["income"] or 0) - float(d["costs"] or 0)
        d["margin_pct"] = (d["profit"] / float(d["income"]) * 100) if d["income"] else None
        result.append(d)
    return result


@app.get("/")
@login_required
def dashboard():
    filters = query_filters()
    where_sql, params = build_where(filters)
    summary = metric_summary(where_sql, params)
    previous = previous_period(filters)
    summary["income_delta"] = delta(summary["income"], previous["income"])
    summary["costs_delta"] = delta(summary["costs"], previous["costs"])
    summary["profit_delta"] = delta(summary["profit"], previous["profit"])
    summary["reservations_delta"] = delta(float(summary["reservations"]), float(previous["reservations"]))

    series = daily_series(where_sql, params)
    units = unit_performance(where_sql, params)
    rows = operations(where_sql, params, 50)
    events = event_profitability(filters)

    return render_template(
        "dashboard.html",
        filters=filters,
        summary=summary,
        series=series,
        units=units,
        operations=rows,
        events=events,
        today=date.today().isoformat(),
    )


@app.get("/operations")
@login_required
def operations_page():
    filters = query_filters()
    where_sql, params = build_where(filters)
    rows = operations(where_sql, params, 250)
    return render_template("operations.html", filters=filters, operations=rows)


@app.post("/operations/new")
@login_required
def new_operation():
    form = request.form
    with connect() as conn:
        conn.execute("""
            INSERT INTO operations (
                created_at, operation_date, operation_type, business_unit, category,
                amount, cost, event_name, customer, people, reservation_status,
                payment_method, notes, telegram_user_id, telegram_username
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            form.get("operation_date") or date.today().isoformat(),
            form.get("operation_type") or "otro",
            form.get("business_unit") or None,
            form.get("category") or None,
            float(form.get("amount") or 0),
            float(form.get("cost") or 0),
            form.get("event_name") or None,
            form.get("customer") or None,
            int(form.get("people")) if form.get("people") else None,
            form.get("reservation_status") or None,
            form.get("payment_method") or None,
            form.get("notes") or None,
            None,
            "dashboard",
        ))
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/operations/<int:operation_id>/delete")
@login_required
def delete_operation(operation_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM operations WHERE id = ?", (operation_id,))
    return redirect(request.referrer or url_for("operations_page"))


@app.get("/api/chart")
@login_required
def chart_api():
    filters = query_filters()
    where_sql, params = build_where(filters)
    return jsonify(daily_series(where_sql, params))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
