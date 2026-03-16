from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ovoz berish", callback_data="vote")],
        [InlineKeyboardButton(text="Loyiha haqida", callback_data="info")]
    ])

def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Bekor qilish", callback_data="cancel")]
    ])

def kb_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Statistika", callback_data="a_stats")],
        [InlineKeyboardButton(text="Broadcast", callback_data="a_broadcast")]
    ])
