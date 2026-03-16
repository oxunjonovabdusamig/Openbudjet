import asyncio
import os
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "0"))
APP_ID = "19bcec1a-1524-4766-9982-9e81ac77a15e"
API = "https://openbudget.uz/api"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
sessions = {}
stats = {"total": 0, "success": 0, "failed": 0}

class S(StatesGroup):
    phone = State()
    code = State()
    broadcast = State()

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

async def api_send_code(phone):
    try:
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(
                API + "/vote/send-code/",
                json={"phone": phone, "application": APP_ID},
                timeout=aiohttp.ClientTimeout(total=15)
            )
            data = await resp.json()
            logger.info("send_code %s: %s", phone, data)
            return data
    except Exception as ex:
        logger.error("send_code error: %s", ex)
        return {}

async def api_vote(token, code):
    try:
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(
                API + "/vote/confirm/",
                json={"token": token, "code": code},
                timeout=aiohttp.ClientTimeout(total=15)
            )
            data = await resp.json()
            logger.info("vote: %s", data)
            return data
    except Exception as ex:
        logger.error("vote error: %s", ex)
        return {}

@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    sessions.pop(m.from_user.id, None)
    stats["total"] += 1
    name = m.from_user.first_name or "Foydalanuvchi"
    text = (
        "Salom, " + name + "!\n\n"
        "Bu bot Beshkapa MFY\n"
        "elektr taminoti loyihasiga\n"
        "ovoz berish uchun.\n\n"
        "Loyiha ID: 053461111011\n"
        "Viloyat: Fargona\n"
        "MFY: Beshkapa"
    )
    await m.answer(text, reply_markup=kb_main())

@dp.message(Command("admin"))
async def cmd_admin(m: types.Message):
    if m.from_user.id != ADMIN:
        await m.answer("Ruxsat yoq!")
        return
    await m.answer("Admin panel:", reply_markup=kb_admin())

@dp.callback_query(F.data == "info")
async def cb_info(call: types.CallbackQuery):
    text = (
        "Loyiha haqida:\n\n"
        "Nomi: Elektr energiyasi taminoti\n"
        "ID: 053461111011\n"
        "Tur: Qurilish va tamirash\n"
        "Maqsad: TP va tayanchilar\n"
        "ornatis hamda tarmoq tortish\n\n"
        "Viloyat: Fargona viloyati\n"
        "Tuman: Ozbekiston tumani\n"
        "MFY: Beshkapa"
    )
    await call.message.edit_text(text, reply_markup=kb_main())
    await call.answer()

@dp.callback_query(F.data == "vote")
async def cb_vote(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Telefon raqamingizni kiriting:\n\n"
        "Format: 998901234567\n"
        "Probelsiz va + belgisiz",
        reply_markup=kb_cancel()
    )
    await state.set_state(S.phone)
    await call.answer()

@dp.callback_query(F.data == "cancel")
async def cb_cancel(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    sessions.pop(call.from_user.id, None)
    await call.message.edit_text("Bekor qilindi.", reply_markup=kb_main())
    await call.answer()

@dp.message(S.phone)
async def on_phone(m: types.Message, state: FSMContext):
    phone = m.text.strip().replace("+", "").replace(" ", "").replace("-", "")
    if not phone.startswith("998") or len(phone) != 12 or not phone.isdigit():
        await m.answer(
            "Notogri format!\n\nTo'gri: 998901234567",
            reply_markup=kb_cancel()
        )
        return
    msg = await m.answer("SMS kod yuborilmoqda...")
    data = await api_send_code(phone)
    if data.get("token"):
        sessions[m.from_user.id] = {"token": data["token"], "phone": phone}
        await msg.edit_text(
            "SMS kod yuborildi!\n\n"
            "Raqamingizga kelgan\n"
            "6 xonali kodni kiriting:",
            reply_markup=kb_cancel()
        )
        await state.set_state(S.code)
    else:
        await msg.edit_text(
            "Xatolik yuz berdi.\n"
            "Javob: " + str(data) + "\n\n"
            "Qayta urining:",
            reply_markup=kb_main()
        )
        await state.clear()

@dp.message(S.code)
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
    res = await api_vote(sess["token"], m.text.strip())
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
        await msg.edit_text(
            "Ovoz berishda xatolik:\n" + str(res) + "\n\n"
            "Qayta urining:",
            reply_markup=kb_main()
        )
    sessions.pop(m.from_user.id, None)
    await state.clear()

@dp.callback_query(F.data == "a_stats")
async def cb_stats(call: types.CallbackQuery):
    if call.from_user.id != ADMIN:
        await call.answer("Ruxsat yoq!", show_alert=True)
        return
    text = (
        "Statistika:\n\n"
        "Jami urinishlar: " + str(stats["total"]) + "\n"
        "Muvaffaqiyatli: " + str(stats["success"]) + "\n"
        "Xato: " + str(stats["failed"]) + "\n"
        "Konversiya: " + str(
            round(stats["success"] / stats["total"] * 100, 1)
            if stats["total"] else 0
        ) + "%"
    )
    await call.message.edit_text(text, reply_markup=kb_admin())
    await call.answer()

@dp.callback_query(F.data == "a_broadcast")
async def cb_broadcast(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN:
        await call.answer("Ruxsat yoq!", show_alert=True)
        return
    await call.message.edit_text(
        "Yuboriladigan xabarni yozing:"
    )
    await state.set_state(S.broadcast)
    await call.answer()

@dp.message(S.broadcast)
async def on_broadcast(m: types.Message, state: FSMContext):
    if m.from_user.id != ADMIN:
        return
    await m.answer("Xabar yuborilmoqda...")
    await state.clear()

async def main():
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
