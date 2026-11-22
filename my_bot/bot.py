import re
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

# Токен більше не зберігається у коді: він читається з .env через config.
# Створення Bot без токена не виконується, щоб модуль можна було імпортувати
# у тестах і перевірках дашборда.
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher(storage=MemoryStorage())

@dp.error()
async def global_error_handler(event: types.ErrorEvent):
    logging.error(f"❌ Глобальна помилка під час обробки: {event.exception}", exc_info=True)
    if event.update.message:
        await event.update.message.answer("⚠️ Ой, щось пішло не так на сервері. Спробуйте ще раз пізніше!")

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

class BookingState(StatesGroup):
    name = State()          # Крок 1: Введення імені
    phone = State()         # Крок 2: Введення телефону (Regex)
    table_number = State()  # Крок 3: Вибір столу
    duration = State()      # Крок 4: Тривалість

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Немає активного діалогу для скасування.", reply_markup=main_keyboard)
        return
    await state.clear()
    await message.answer("❌ Бронювання скасовано.", reply_markup=main_keyboard)

@dp.message(Command("book"))
@dp.message(F.text == BTN_BOOK)
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(BookingState.name)
    await message.answer(
        "📝 **Бронювання столу у SmartHub NUBiP!**\n"
        "Введіть ваше ім'я та прізвище (мінімум 2 символи):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(BookingState.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if len(name) < 2 or not re.match(r"^[a-zA-Zа-яА-ЯіІїЇєЄ\'\s]+$", name):
        await message.answer("⚠️ Будь ласка, введіть коректне ім'я (без спецсимволів і цифр, мінімум 2 літери):")
        return
    
    await state.update_data(user_name=name)
    await state.set_state(BookingState.phone)
    await message.answer("Введіть ваш номер телефону у форматі **0XXXXXXXXX** (наприклад, 0671234567):", parse_mode="Markdown")

@dp.message(BookingState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone_text = message.text.strip() if message.text else ""
    # Перевірка через Regex
    if not re.match(r"^0\d{9}$", phone_text):
        await message.answer("⚠️ Некоректний формат телефону! Формат: 10 цифр, що починаються з 0 (наприклад: `0671234567`):", parse_mode="Markdown")
        return

    await state.update_data(phone=phone_text)
    await state.set_state(BookingState.table_number)
    await message.answer("Введіть номер столу (від 1 до 10):")

@dp.message(BookingState.table_number)
async def process_table(message: types.Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text.isdigit() or not (1 <= int(text) <= 10):
        await message.answer("⚠️ Номер столу має бути цілим числом від 1 до 10!")
        return

    await state.update_data(table_num=text)
    await state.set_state(BookingState.duration)
    await message.answer("На скільки годин бронюєте місце? (від 1 до 8 годин):")

@dp.message(BookingState.duration)
async def process_duration(message: types.Message, state: FSMContext):
    try:
        hours = int(message.text.strip())
        if not (1 <= hours <= 8):
            raise ValueError("Вихід за межі")
    except (ValueError, AttributeError):
        await message.answer("⚠️ Введіть коректну кількість годин (ціле число від 1 до 8):")
        return

    await state.update_data(hours=hours)
    user_data = await state.get_data()
    
    summary = (
        "✅ **Бронювання успішно створено!**\n\n"
        f"👤 **Студент:** {user_data.get('user_name')}\n"
        f"📞 **Тел:** {user_data.get('phone')}\n"
        f"🪑 **Стіл №:** {user_data.get('table_num')}\n"
        f"⏱ **Тривалість:** {user_data.get('hours')} год."
    )
    await message.answer(summary, parse_mode="Markdown", reply_markup=main_keyboard)
    await state.clear()

@dp.message(Command("checkin"))
@dp.message(F.text == BTN_CHECKIN)
async def checkin_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("📲 Для підтвердження введіть код столу у форматі `HUB-XX` (наприклад: `/checkin HUB-05`):", parse_mode="Markdown")
        return
    
    qr_code = parts[1].strip().upper()
    if not re.match(r"^HUB-\d{2}$", qr_code):
        await message.answer("⚠️ Некоректний код столу! Формат повинен бути **HUB-XX** (наприклад: `HUB-02`).", parse_mode="Markdown")
        return

    await message.answer(f"✅ Присутність успішно підтверджено для столу **{qr_code}**!", parse_mode="Markdown")

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    try:
        username = message.from_user.username if message.from_user and message.from_user.username else "Студент"
        await message.answer(f"Привіт, @{username}! Вітаємо у SmartHub NUBiP.", reply_markup=main_keyboard)
    except Exception as e:
        logging.error(f"Помилка у /start: {e}")
        await message.answer("Вітаємо у SmartHub NUBiP!", reply_markup=main_keyboard)

@dp.message(Command("help"))
@dp.message(F.text == BTN_HELP)
async def help_handler(message: types.Message):
    await message.answer("📋 Доступні команди: /book (бронювання), /checkin HUB-01 (підтвердження), /check 25 (стан залу).")

@dp.message(Command("free"))
@dp.message(F.text == BTN_FREE)
async def free_handler(message: types.Message):
    await message.answer("🟢 Доступні місця: Стіл №1, Стіл №2, Стіл №5")

@dp.message()
async def echo_handler(message: types.Message):
    await message.answer("Я не зрозумів команду. Напишіть /help або скористайтесь меню.")

async def main():
    if bot is None:
        raise SystemExit("❌ Не знайдено BOT_TOKEN у файлі .env!")
    print(">>> Захищений бот (Lab 7) успішно запущений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())