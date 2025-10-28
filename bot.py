import os, asyncio, datetime as dt
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON")
MASTER_SPREADSHEET_ID = os.getenv("MASTER_SPREADSHEET_ID")

def gs_client():
    import json
    data = json.loads(GOOGLE_SA_JSON)
    creds = Credentials.from_service_account_info(
        data,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

gc = gs_client()
sh = gc.open_by_key(MASTER_SPREADSHEET_ID)

def ws(name: str):
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=name, rows=1000, cols=20)

intake_ws = ws("Intake")
content_ws = ws("Content")

def read_content() -> Dict[str, str]:
    rows = content_ws.get_all_values()
    d = {}
    for r in rows[1:]:
        if len(r) >= 2 and r[0]:
            d[r[0]] = r[1]
    return d

def append_intake(uid, uname, action):
    intake_ws.append_row([
        dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        uid, uname or "", action
    ], value_input_option="USER_ENTERED")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = read_content()
    text = content.get("start_intro_text", "Привет! Я бот тренировочного дневника.")
    kb = [
        [InlineKeyboardButton("Хочу ознакомиться", callback_data="learn_more")],
        [InlineKeyboardButton("Я действующий подопечный", callback_data="current")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    content = read_content()
    user = update.effective_user

    if q.data == "learn_more":
        append_intake(user.id, user.username, "learn")
        text = content.get("learn_more_text", "Презентация дневника и условия…")
        trainer_username = content.get("trainer_username", "bezha_nova")
        kb = [[InlineKeyboardButton("Перейти к тренеру", url=f"https://t.me/{trainer_username}")]]
        await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "current":
        append_intake(user.id, user.username, "current")
        text = content.get("active_soon_text", "Скоро здесь появятся твои тренировки.")
        await q.message.reply_text(text)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
