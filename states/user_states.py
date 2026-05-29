from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    looking_for = State()
    city = State()
    location = State()
    bio = State()
    photo = State()
    confirm = State()


class EditProfile(StatesGroup):
    choose_field = State()
    name = State()
    age = State()
    city = State()
    location = State()
    bio = State()
    photo = State()
    looking_for = State()


class ReportFlow(StatesGroup):
    reason = State()


class AdminFlow(StatesGroup):
    broadcast = State()
    ban_user = State()
    unban_user = State()
    seed_photo = State()
