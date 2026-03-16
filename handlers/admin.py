import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
from states import AdminState
from keyboards import kb_admin
from handlers.user import get_stats

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

@router.message(Command("admin"))
async def cmd_admin(m: types.Message):
    if not is_admin(m.from_user.id):
        await m.answer("Ruxsat yoq!")
        return
    await m.answer("Admin panel:", reply_markup=kb_admin())

@router.callback_query(F.data == "a_stats")
async def cb_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yoq!", show_alert=True)
        return
    s = get_stats()
    total = s["total"]
    success = s["success"]
    failed = s["failed"]
    conv = round(success / total * 100, 1) if total else 0
    await call.message.edit_text(
        "Statistika:\n\n"
        "Jami urinishlar: " + str(total) + "\n"
        "Muvaffaqiyatli: " + str(success) + "\n"
        "Xato: " + str(failed) + "\n"
        "Konversiya: " + str(conv) + "%",
        reply_markup=kb_admin()
    )
    await call.answer()

@router.callback_query(F.data == "a_broadcast")
async def cb_broadcast(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yoq!", show_alert=True)
        return
    await call.message.edit_text("Yuboriladigan xabarni yozing:")
    await state.set_state(AdminState.broadcast)
    await call.answer()

@router.message(AdminState.broadcast)
async def on_broadcast(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await m.answer("Xabar yuborildi!")
    await state.clear()
