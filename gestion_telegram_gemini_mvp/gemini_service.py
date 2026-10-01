from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
import requests

from config import GEMINI_API_KEY, GEMINI_MODEL


class ParsedMessage(BaseModel):
    kind: Literal["record", "query", "unknown"]

    # Campos de registro
    operation_type: Optional[
        Literal["venta", "compra", "gasto", "cobro", "ingreso", "devolucion", "reserva", "evento", "otro"]
    ] = None
    business_unit: Optional[Literal["bar", "salon", "catering", "otro"]] = None
    category: Optional[str] = None
    amount: float = 0
    cost: float = 0
    operation_date: Optional[str] = None
    event_name: Optional[str] = None
    customer: Optional[str] = None
    people: Optional[int] = None
    reservation_status: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

    # Campos de consulta
    metric: Optional[
        Literal[
            "summary", "income", "costs", "profit", "margin",
            "reservations", "confirmed_reservations", "records"
        ]
    ] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


def _generate_content(
    prompt: str,
    *,
    system_instruction: str | None = None,
    temperature: float = 0,
    response_schema: dict[str, Any] | None = None,
) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("Falta GEMINI_API_KEY en el archivo .env")

    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if response_schema:
        payload["generationConfig"].update(
            {
                "responseMimeType": "application/json",
                "responseJsonSchema": response_schema,
            }
        )

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (IndexError, KeyError, TypeError) as exc:
        raise RuntimeError("Gemini no devolvió contenido utilizable") from exc


def parse_message(text: str) -> ParsedMessage:
    today = date.today().isoformat()

    system = f"""
Sos el motor de interpretación de un sistema de gestión para tres unidades:
bar, salon y catering.

Fecha actual: {today}.

Tu única tarea es convertir el mensaje del usuario al esquema JSON indicado.

REGLAS:
1. Si el usuario informa una operación para guardar, kind="record".
2. Si pregunta sobre información del negocio, kind="query".
3. Si no se puede determinar, kind="unknown".
4. Normalizá importes argentinos:
   - "185 mil" = 185000
   - "1,8 millones" = 1800000
   - "$850.000" = 850000
5. operation_date, date_from y date_to deben ser YYYY-MM-DD.
6. "hoy" = {today}.
7. Para una consulta de margen de un evento: metric="margin" y event_name con el nombre.
8. Para "cuánto vendimos/recaudamos/facturamos": metric="income".
9. Para "cuánto gastamos/costos": metric="costs".
10. Para "ganancia/resultado": metric="profit".
11. Para una reserva, amount representa una seña/cobro asociado si fue mencionado.
12. Si un mensaje dice algo como "evento López cobré 850000, gastos 510000",
    usar operation_type="evento", amount=850000, cost=510000.
13. No inventes datos faltantes.
"""

    response_text = _generate_content(
        text,
        system_instruction=system,
        response_schema=ParsedMessage.model_json_schema(),
    )
    return ParsedMessage.model_validate_json(response_text)


def answer_from_results(question: str, parsed: ParsedMessage, stats: dict) -> str:
    # Los cálculos vienen de SQLite. Gemini solo redacta la respuesta.
    prompt = f"""
Pregunta original:
{question}

Consulta interpretada:
{parsed.model_dump_json()}

Resultado REAL calculado por la base de datos:
{stats}

Respondé en español rioplatense, de forma breve, profesional y clara.
No inventes datos.
Si margin_pct es None, explicá que no hay ingresos suficientes para calcular margen.
Mostrá montos en pesos con separador de miles.
Si es útil, mostrÁ ingreso, costos, resultado y margen.
"""
    return _generate_content(prompt, temperature=0.2).strip()
