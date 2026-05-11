import json
import logging
import os
import re
from datetime import date

import gspread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "8721870314:AAEVSVj2gy1Gu0BeDUHtFH9x4nEgsbCB3ao")
SHEET_ID = os.getenv("SHEET_ID", "16ubX8tkwshnbiqbQKkRdJsO_S_jkBjeui1M6Xu76W7A")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json:
    gc = gspread.service_account_from_dict(json.loads(creds_json))
else:
    gc = gspread.service_account(filename="credenciales.json")

sh = gc.open_by_key(SHEET_ID)


def agregar_gasto(texto: str) -> str:
    match = re.match(r"(.+?)\s+(\d+[\d.]*)$", texto.strip())
    if not match:
        return "Formato: concepto monto. Ej: supermercado 5000"
    concepto = match.group(1).strip().lower().capitalize()
    monto = float(match.group(2).replace(".", "").replace(",", "."))
    try:
        ws = sh.worksheet("detalle gastos")
    except Exception:
        return "Error al conectar con Google Sheets."
    ws.append_row([str(date.today()), concepto, monto])
    return f"Agregado: {concepto} ${monto:,.0f}"


async def start(update: Update, _context):
    await update.message.reply_text(
        "Hola! Mandame un gasto así:\n"
        "supermercado 5000\n\n"
        "O usá /total o /gastos"
    )


async def total(update: Update, _context):
    try:
        ws = sh.worksheet("detalle gastos")
    except Exception:
        await update.message.reply_text("Error al conectar con Google Sheets.")
        return
    registros = ws.get_all_values()[1:]
    total = 0
    for row in registros:
        if len(row) >= 3 and row[2]:
            try:
                total += float(row[2])
            except ValueError:
                pass
    await update.message.reply_text(f"Total gastos: ${total:,.0f}")


async def gastos(update: Update, _context):
    try:
        ws = sh.worksheet("detalle gastos")
    except Exception:
        await update.message.reply_text("Error al conectar con Google Sheets.")
        return
    registros = ws.get_all_values()[1:]
    if not registros:
        await update.message.reply_text("No hay gastos registrados.")
        return
    lineas = []
    for r in registros[-10:]:
        if len(r) >= 3 and r[2]:
            lineas.append(f"{r[0]} | {r[1]} | ${r[2]}")
    await update.message.reply_text("Últimos gastos:\n" + "\n".join(lineas))


async def manejar_mensaje(update: Update, _context):
    if not update.message or not update.message.text:
        return
    respuesta = agregar_gasto(update.message.text)
    await update.message.reply_text(respuesta)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("gastos", gastos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    print("Bot iniciado (Google Sheets). Presioná Ctrl+C para detenerlo.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
