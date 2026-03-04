from aiogram.fsm.state import State, StatesGroup


class TestFlow(StatesGroup):
    in_test = State()
