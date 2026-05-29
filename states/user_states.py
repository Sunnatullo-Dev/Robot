from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    location = State()
    bio = State()
    photo = State()
    confirm = State()


class EditProfile(StatesGroup):
    name = State()
    age = State()
    city = State()
    location = State()
    bio = State()
    photo = State()


class ReportFlow(StatesGroup):
    reason = State()


class AdminFlow(StatesGroup):
    broadcast = State()
    broadcast_filter_region = State()
    ban_user = State()
    unban_user = State()
    seed_photo = State()
    user_search = State()
    setting_value = State()
