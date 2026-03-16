import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import VoteState
from keyboards import kb_main, kb_cancel
from api import send_code, confirm_vote

logger = logging.getLogger(__name__)
router = Router()
sessions = {}
stats = {"total": 0, "success": 0, "failed": 0}

def get_stats():
    return stats

@router.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    sessions.pop(m.from_user.id, None)
    stats["total"] += 1
    name = m.from_user.first_name or "Foydalanuvchi"
    await m.answer(
        "Salom, " + name + "!\n\n"
        "Bu bot Beshkapa MFY\n"
        "elektr taminoti loyihasiga\n"
        "ovoz berish uchun.\n\n"
        "Loyiha ID: 053461111011\n"
        "Viloyat: Fargona\n"
        "MFY: Beshkapa",
        reply_markup=kb_main()
    )

@router.callback_query(F.data == "info")
async def cb_info(call: types.CallbackQuery):
    await call.message.edit_text(
        "Loyiha haqida:\n\n"
        "Nomi: Elektr energiyasi taminoti\n"
        "ID: 053461111011\n"
        "Tur: Qurilish va tamirash\n"
        "Maqsad: TP va tayanchilar\n"
        "ornatis hamda tarmoq tortish\n\n"
        "Viloyat: Fargona viloyati\n"
        "Tuman: Ozbekiston tumani\n"
        "MFY: Beshkapa",
        reply_markup=kb_main()
    )
    await call.answer()

@router.callback_query(F.data == "vote")
async def cb_vote(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Telefon raqamingizni kiriting:\n\n"
        "Format: 998901234567\n"
        "Probelsiz va + belgisiz",
        reply_markup=kb_cancel()
    )
    await state.set_state(VoteState.phone)
    await call.answer()

@router.callback_query(F.data == "cancel")
async def cb_cancel(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    sessions.pop(call.from_user.id, None)
    await call.message.edit_text("Bekor qilindi.", reply_markup=kb_main())
    await call.answer()

@router.message(VoteState.phone)
async def on_phone(m: types.Message, state: FSMContext):
    phone = m.text.strip().replace("+", "").replace(" ", "").replace("-", "")
    if not phone.startswith("998") or len(phone) != 12 or not phone.isdigit():
        await m.answer(
            "Notogri format!\n\nTogri: 998901234567",
            reply_markup=kb_cancel()
        )
        return
    msg = await m.answer("SMS kod yuborilmoqda...")
    data = await send_code(phone)
    if data.get("token"):
        sessions[m.from_user.id] = {"token": data["token"], "phone": phone}
        await msg.edit_text(
            "SMS kod yuborildi!\n\n"
            "Raqamingizga kelgan\n"
            "6 xonali kodni kiriting:",
            reply_markup=kb_cancel()
        )
        await state.set_state(VoteState.code)
    else:
        err = data.get("error") or data.get("detail") or data.get("raw") or str(data)
        await msg.edit_text(
            "Xatolik: " + str(err) + "\n\nQayta urining:",
            reply_markup=kb_main()
        )
        await state.clear()

@router.message(VoteState.code)
async def on_code(m: types.Message, state: FSMContext):
    sess = sessions.get(m.from_user.id)
    if not sess:
        await m.answer("Sessiya topilmadi.", reply_markup=kb_main())
        await state.clear()
        return
    if not m.text.strip().isdigit():
        await m.answer("Faqat raqam kiriting!", reply_markup=kb_cancel())
        return
    msg = await m.answer("Ovoz berilmoqda...")
    res = await confirm_vote(sess["token"], m.text.strip())
    if res.get("success") or res.get("status") == "ok":
        stats["success"] += 1
        await msg.edit_text(
            "Ovozingiz qabul qilindi!\n\n"
            "Beshkapa MFY elektr taminoti\n"
            "loyihasiga muvaffaqiyatli\n"
            "ovoz berdingiz!\n\n"
            "Ishtirokingiz uchun rahmat!"
        )
    else:
        stats["failed"] += 1
        err = res.get("error") or res.get("detail") or res.get("raw") or str(res)
        await msg.edit_text(
            "Xatolik: " + str(err) + "\n\nQayta urining:",
            reply_markup=kb_main()
        )
    sessions.pop(m.from_user.id, None)
    await state.clear()
