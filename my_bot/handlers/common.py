from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from keyboards import BTN_FREE, BTN_HELP, main_keyboard
from storage import get_user

router = Router()

@router.message(CommandStart())
async def start_handler(message: types.Message):
    username = message.from_user.username if message.from_user and message.from_user.username else "Студент"
    await message.answer(f"Привіт, @{username}! Вітаємо у SmartHub NUBiP.", reply_markup=main_keyboard)

# Команда /me для перевірки профілю з JSON
@router.message(Command("me"))
async def me_handler(message: types.Message):
    user = get_user(message.from_user.id)
    if user is None:
        await message.answer("Ви ще не зареєстровані та не робили бронювань. Використайте /book")
        return
    
    await message.answer(
        f"👤 **Ваш профіль у базі:**\n"
        f"• Ім'я: {user.get('name')}\n"
        f"• Телефон: {user.get('phone')}\n"
        f"• Дата реєстрації: {user.get('createdAt')}",
        parse_mode="Markdown"
    )

@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def help_handler(message: types.Message):
    await message.answer("📋 Команди: /book, /me (мій профіль), /checkin HUB-01, /check 25")

@router.message(Command("free"))
@router.message(F.text == BTN_FREE)
async def free_handler(message: types.Message):
    await message.answer("🟢 Доступні місця: Стіл №1, Стіл №2, Стіл №5")

@router.message()
async def echo_handler(message: types.Message):
    await message.answer("Я не зрозумів команду. Напишіть /help або скористайтесь меню.")