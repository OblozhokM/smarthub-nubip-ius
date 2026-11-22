from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BTN_FREE = "🟢 Вільні місця"
BTN_BOOK = "📅 Забронювати"
BTN_CHECKIN = "📲 Check-in (QR)"
BTN_HELP = "❓ Допомога"

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_FREE), KeyboardButton(text=BTN_BOOK)],
        [KeyboardButton(text=BTN_CHECKIN), KeyboardButton(text=BTN_HELP)],
    ],
    resize_keyboard=True
)