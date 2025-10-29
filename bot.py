import os, logging, json, datetime as dt
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("MASTER_SPREADSHEET_ID")
GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON")

def gs_client():
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_SA_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

gc = gs_client()
sh = gc.open_by_key(SPREADSHEET_ID)

def get_ws(name: str):
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=name, rows=1000, cols=20)

content_ws = get_ws("Content")
intake_ws = get_ws("Intake")

def get_text(key: str) -> str:
    try:
        rows = content_ws.get_all_values()
        for r in rows[1:]:
            if len(r) >= 2 and r[0] == key:
                return r[1]
    except Exception as e:
        logging.error(f"get_text error: {e}")
    return "..."

def log_intake(uid, uname, action):
    try:
        intake_ws.append_row([
            dt.datetime.utcnow().isoformat(timespec="seconds")+"Z",
            uid, uname or "", action
        ], value_input_option="USER_ENTERED")
    except Exception as e:
        logging.error(f"intake append error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Хочу ознакомиться", callback_data="learn")],
        [InlineKeyboardButton("Я действующий подопечный", callback_data="current")]
    ]
    await update.message.reply_text(get_text("start_intro_text"), reply_markup=InlineKeyboardMarkup(kb))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = update.effective_user

    if q.data == "learn":
        log_intake(user.id, user.username, "learn")
        trainer = get_text("trainer_username") or "bezha_nova"
        kb = [[InlineKeyboardButton("Перейти к тренеру", url=f"https://t.me/{trainer}")]]
        await q.edit_message_text(get_text("learn_more_text"), reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "current":
        log_intake(user.id, user.username, "current")
        await q.edit_message_text(get_text("active_soon_text"))
    else:
        await q.edit_message_text("Ошибка, попробуй ещё раз.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    logging.info("Bot polling started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
