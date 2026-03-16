from aiogram.fsm.state import State, StatesGroup

class VoteState(StatesGroup):
    phone = State()
    code = State()

class AdminState(StatesGroup):
    broadcast = State()
