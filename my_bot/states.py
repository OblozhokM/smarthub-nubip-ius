from aiogram.fsm.state import StatesGroup, State

class BookingState(StatesGroup):
    name = State()
    phone = State()
    table_number = State()
    duration = State()