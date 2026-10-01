import logging
from datetime import date

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    ALLOWED_TELEGRAM_USERS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    TELEGRAM_BOT_TOKEN,
)
from database import aggregate, init_db, insert_operation, recent_operations, seed_demo
from gemini_service import ParsedMessage, answer_from_results, parse_message


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("gestion-bot")

MENU_REGISTER = "➕ Registrar operación"
MENU_QUERY = "📊 Consultar resultados"
MENU_LATEST = "📋 Últimas operaciones"
MENU_HELP = "❓ Cómo usar el bot"

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [MENU_REGISTER, MENU_QUERY],
        [MENU_LATEST, MENU_HELP],
    ],
    resize_keyboard=True,
    input_field_placeholder="Escribí una operación o elegí una opción…",
)


def usage_guide() -> str:
    return (
        "🤖 <b>Asistente de Gestión</b>\n\n"
        "Elegí una opción del teclado o escribime en lenguaje natural. "
        "Antes de guardar, siempre te pediré confirmación.\n\n"
        "<b>Para registrar</b>\n"
        "• Compré bebidas para el bar por $185.000\n"
        "• Evento López: cobré 850 mil y gasté 510 mil\n"
        "• Reserva Juan Pérez, 8 personas, confirmada, seña 120 mil\n\n"
        "<b>Para consultar</b>\n"
        "• ¿Cuánto vendimos hoy?\n"
        "• ¿Cuál fue el margen del evento López?\n"
        "• ¿Cuánto gastamos hoy en el bar?\n\n"
        "<b>Comandos</b>\n"
        "/menu — mostrar esta guía\n"
        "/ultimos — ver los últimos movimientos\n"
        "/demo — cargar datos ficticios de prueba\n"
        "/id — ver tu ID de Telegram"
    )


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    return not ALLOWED_TELEGRAM_USERS or user.id in ALLOWED_TELEGRAM_USERS


async def deny(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ Tu usuario no está habilitado para usar este bot."
        )


def money(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def record_preview(p: ParsedMessage) -> str:
    lines = [
        "🧾 <b>Detecté una operación</b>",
        "",
        f"<b>Tipo:</b> {p.operation_type or '—'}",
        f"<b>Unidad:</b> {p.business_unit or '—'}",
    ]

    if p.category:
        lines.append(f"<b>Categoría:</b> {p.category}")
    if p.amount:
        lines.append(f"<b>Importe:</b> {money(p.amount)}")
    if p.cost:
        lines.append(f"<b>Costo:</b> {money(p.cost)}")
    if p.event_name:
        lines.append(f"<b>Evento:</b> {p.event_name}")
    if p.customer:
        lines.append(f"<b>Cliente:</b> {p.customer}")
    if p.people:
        lines.append(f"<b>Personas:</b> {p.people}")
    if p.reservation_status:
        lines.append(f"<b>Estado reserva:</b> {p.reservation_status}")

    lines.append(f"<b>Fecha:</b> {p.operation_date or date.today().isoformat()}")
    lines.extend(["", "¿Guardar esta operación?"])
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await deny(update)
        return

    await update.message.reply_text(
        usage_guide(),
        parse_mode="HTML",
        reply_markup=MAIN_MENU,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    await update.message.reply_text(
        f"Tu Telegram ID es: {update.effective_user.id}"
    )


async def demo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await deny(update)
        return

    u = update.effective_user
    ids = seed_demo(u.id, u.username)
    await update.message.reply_text(
        "✅ Cargué 3 operaciones de demostración.\n\n"
        "Probá preguntar:\n"
        "• ¿Cuál fue el margen del evento López?\n"
        "• ¿Cuánto vendimos hoy?\n"
        "• ¿Cuántas reservas confirmadas tenemos hoy?\n\n"
        f"IDs creados: {', '.join(map(str, ids))}"
    )


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await deny(update)
        return

    rows = recent_operations(10)
    if not rows:
        await update.message.reply_text("Todavía no hay operaciones.")
        return

    lines = ["📋 <b>Últimas operaciones</b>", ""]
    for r in rows:
        detail = r["event_name"] or r["customer"] or r["category"] or ""
        lines.append(
            f"#{r['id']} · {r['operation_date']} · "
            f"{r['business_unit'] or '—'} · {r['operation_type']} · "
            f"{money(r['amount'])} {detail}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await deny(update)
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    if text == MENU_REGISTER:
        await update.message.reply_text(
            "➕ <b>Registrar operación</b>\n\n"
            "Contame el movimiento con importe y unidad de negocio.\n\n"
            "Ejemplo: <i>Compré bebidas para el bar por $185.000</i>",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )
        return

    if text == MENU_QUERY:
        await update.message.reply_text(
            "📊 <b>Consultar resultados</b>\n\n"
            "Podés preguntar por ventas, costos, resultado, margen o reservas.\n\n"
            "Ejemplo: <i>¿Cuánto vendimos hoy?</i>",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )
        return

    if text == MENU_LATEST:
        await latest_command(update, context)
        return

    if text == MENU_HELP:
        await start(update, context)
        return

    await update.message.chat.send_action("typing")

    try:
        parsed = parse_message(text)
    except Exception as exc:
        logger.exception("Error interpretando mensaje")
        await update.message.reply_text(
            "⚠️ No pude consultar Gemini.\n"
            f"Detalle: {type(exc).__name__}: {exc}"
        )
        return

    if parsed.kind == "record":
        payload = parsed.model_dump()
        payload["operation_date"] = payload.get("operation_date") or date.today().isoformat()

        context.user_data["pending_operation"] = payload

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm_record"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_record"),
        ]])

        await update.message.reply_text(
            record_preview(parsed),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if parsed.kind == "query":
        query_filters = {
            "business_unit": parsed.business_unit,
            "event_name": parsed.event_name,
            "category": parsed.category,
            "date_from": parsed.date_from,
            "date_to": parsed.date_to,
        }

        # Si la pregunta contiene "hoy" pero Gemini no fijó fecha, aseguramos el filtro.
        if "hoy" in text.lower() and not parsed.date_from and not parsed.date_to:
            query_filters["date_from"] = date.today().isoformat()
            query_filters["date_to"] = date.today().isoformat()

        stats = aggregate(query_filters)
        try:
            answer = answer_from_results(text, parsed, stats)
        except Exception:
            logger.exception("Error redactando respuesta")
            margin = (
                f"{stats['margin_pct']:.1f}%"
                if stats["margin_pct"] is not None else "N/D"
            )
            answer = (
                f"Ingresos: {money(stats['income'])}\n"
                f"Costos: {money(stats['total_costs'])}\n"
                f"Resultado: {money(stats['profit'])}\n"
                f"Margen: {margin}\n"
                f"Registros: {stats['records']}"
            )

        await update.message.reply_text(answer)
        return

    await update.message.reply_text(
        "No pude determinar si querés registrar una operación o hacer una consulta.\n\n"
        "Probá, por ejemplo:\n"
        "“Vendimos $250.000 en el bar”\n"
        "o\n"
        "“¿Cuánto vendimos hoy?”"
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("⛔ Usuario no habilitado.")
        return

    if query.data == "cancel_record":
        context.user_data.pop("pending_operation", None)
        await query.edit_message_text("❌ Operación cancelada.")
        return

    if query.data == "confirm_record":
        data = context.user_data.pop("pending_operation", None)
        if not data:
            await query.edit_message_text(
                "⚠️ La operación pendiente ya no está disponible. Enviála nuevamente."
            )
            return

        user = update.effective_user
        operation_id = insert_operation(data, user.id, user.username)
        await query.edit_message_text(
            f"✅ Operación guardada correctamente.\nID: #{operation_id}"
        )


async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("menu", "ver guía y opciones"),
        BotCommand("ultimos", "ver últimos movimientos"),
        BotCommand("demo", "cargar datos de demostración"),
        BotCommand("id", "ver mi ID de Telegram"),
        BotCommand("help", "ver ayuda"),
    ])


def validate_config():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if missing:
        raise RuntimeError(
            "Faltan variables en .env: " + ", ".join(missing)
        )


def main():
    validate_config()
    init_db()

    print("=" * 60)
    print("ASISTENTE DE GESTIÓN - MVP")
    print(f"Modelo Gemini: {GEMINI_MODEL}")
    print("Base de datos: gestion.db")
    print("Bot iniciado. Presioná Ctrl+C para detener.")
    print("=" * 60)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("demo", demo_command))
    app.add_handler(CommandHandler("ultimos", latest_command))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
