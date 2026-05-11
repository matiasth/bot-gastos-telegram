import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import date

import gspread
import speech_recognition as sr
from imageio_ffmpeg import get_ffmpeg_exe
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "8721870314:AAEVSVj2gy1Gu0BeDUHtFH9x4nEgsbCB3ao")
SHEET_ID = os.getenv("SHEET_ID", "16ubX8tkwshnbiqbQKkRdJsO_S_jkBjeui1M6Xu76W7A")

FFMPEG = get_ffmpeg_exe()

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
        "Hola! Mandame un gasto:\n"
        "supermercado 5000  (texto)\n"
        "O mandame un audio de voz y lo reconozco"
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


async def manejar_voz(update: Update, context):
    msg = await update.message.reply_text("Escuchando...")
    try:
        voz = update.message.voice
        archivo = await context.bot.get_file(voz.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f_ogg:
            await archivo.download_to_drive(f_ogg.name)
            ogg_path = f_ogg.name
        wav_path = ogg_path.replace(".ogg", ".wav")
        subprocess.run([FFMPEG, "-y", "-i", ogg_path, wav_path], capture_output=True)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        texto = recognizer.recognize_google(audio, language="es-AR")
        os.unlink(ogg_path)
        os.unlink(wav_path)
        await msg.edit_text(f"Reconocí: {texto}")
        respuesta = agregar_gasto(texto)
        await msg.reply_text(respuesta)
    except sr.UnknownValueError:
        await msg.edit_text("No entendí el audio.")
    except sr.RequestError:
        await msg.edit_text("Error al conectar con el servicio de voz.")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)[:200]}")


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
    app.add_handler(MessageHandler(filters.VOICE, manejar_voz))
    print("Bot iniciado (texto + voz). Presioná Ctrl+C para detenerlo.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
