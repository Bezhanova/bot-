import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- ЛОГИ ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- ЧТЕНИЕ ПЕРЕМЕННЫХ ИЗ ОКРУЖЕНИЯ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("MASTER_SPREADSHEET_ID")
GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON")

# --- НАСТРОЙКА ДОСТУПА К GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(GOOGLE_SA_JSON), scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID)

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: получение текста из таблицы ---
def get_text(key: str) -> str:
    try:
        worksheet = sheet.worksheet("Content")
        data = worksheet.get_all_records()
        for row in data:
            if row["key"] == key:
                return row["value"]
    except Exception as e:
        logging.error(f"Ошибка при получении текста: {e}")
    return "Текст не найден."

# --- ОБРАБОТЧИК /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Хочу ознакомиться", callback_data="learn")],
        [InlineKeyboardButton("Я действующий подопечный", callback_data="current")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text("start_intro_text"), reply_markup=reply_markup)

# --- ОБРАБОТКА НАЖАТИЙ КНОПОК ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    user = query.from_user

    # Запись данных в Intake
    try:
        intake_sheet = sheet.worksheet("Intake")
        intake_sheet.append_row([str(user.id), user.username, action])
    except Exception as e:
        logging.error(f"Ошибка записи в Intake: {e}")

    if action == "learn":
        await query.edit_message_text(get_text("learn_more_text"))
    elif action == "current":
        await query.edit_message_text(get_text("active_soon_text"))
    else:
        await query.edit_message_text("Ошибка, попробуй снова.")

# --- ЗАПУСК БОТА ---
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    logging.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
