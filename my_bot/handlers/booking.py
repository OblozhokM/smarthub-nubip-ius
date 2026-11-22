from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from keyboards import BTN_BOOK, main_keyboard
from states import BookingState
from utils.validators import validate_phone
from utils.format import NOT_FOUND_TEXT, SAVE_FAILED_TEXT, format_booking
import storage

router = Router()

# ПІДТВЕРДЖЕННЯ ВИДАЛЕННЯ (Delete Confirmation)
@router.message(F.state == "confirm_delete")
async def process_confirm_delete(message: types.Message, state: FSMContext):
    text = message.text.strip().lower() if message.text else ""
    if text != "так":
        await state.clear()
        await message.answer("❌ Видалення скасовано.", reply_markup=main_keyboard)
        return
    data = await state.get_data()
    b_id = data.get("delete_id")
    await state.clear()
    try:
        removed = storage.delete_booking(b_id, message.from_user.id)
        if removed is None:
            await message.answer(NOT_FOUND_TEXT, reply_markup=main_keyboard)
            return
        await message.answer("🗑 **Видалено бронювання:**\n" + format_booking(removed), parse_mode="Markdown", reply_markup=main_keyboard)
    except Exception:
        await message.answer(SAVE_FAILED_TEXT, reply_markup=main_keyboard)

@router.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Немає активного діалогу для скасування.", reply_markup=main_keyboard)
        return
    await state.clear()
    await message.answer("❌ Дійсно скасовано.", reply_markup=main_keyboard)

@router.message(Command("book"))
@router.message(F.text == BTN_BOOK)
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(BookingState.name)
    await message.answer("📝 Введіть ваше ім'я та прізвище:", reply_markup=ReplyKeyboardRemove())

@router.message(BookingState.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("⚠️ Введіть ім'я (мінімум 2 літери):")
        return
    await state.update_data(user_name=name)
    await state.set_state(BookingState.phone)
    await message.answer("Введіть телефон у форматі 0XXXXXXXXX:")

@router.message(BookingState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip() if message.text else ""
    if not validate_phone(phone):
        await message.answer("⚠️ Формат телефону: 0XXXXXXXXX (наприклад, 0671234567)")
        return
    await state.update_data(phone=phone)
    await state.set_state(BookingState.table_number)
    await message.answer("Введіть номер столу (1-10):")

@router.message(BookingState.table_number)
async def process_table(message: types.Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text.isdigit() or not (1 <= int(text) <= 10):
        await message.answer("⚠️ Номер столу має бути від 1 до 10!")
        return
    await state.update_data(table_num=int(text))
    await state.set_state(BookingState.duration)
    await message.answer("На скільки годин (1-8):")

@router.message(BookingState.duration)
async def process_duration(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text.strip().replace(',', '.'))
        if not (1 <= hours <= 8):
            raise ValueError()
    except Exception:
        await message.answer("⚠️ Введіть число від 1 до 8:")
        return
        
    await state.update_data(hours=hours)
    user_data = await state.get_data()
    
    storage.save_user(
        message.from_user.id,
        name=user_data.get("user_name"),
        phone=user_data.get("phone"),
    )
    rec = storage.add_booking(message.from_user.id, user_data.get("user_name"), user_data.get("table_num"), hours)
    await state.clear()

    summary = "✅ **Бронювання збережено!**\n" + format_booking(rec)
    await message.answer(summary, parse_mode="Markdown", reply_markup=main_keyboard)