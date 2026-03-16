import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== SOZLAMALAR =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
APPLICATION_ID = "19bcec1a-1524-4766-9982-9e81ac77a15e"
BASE_URL = "https://openbudget.uz/api"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== HOLATLAR =====
class VoteState(StatesGroup):
    waiting_phone = State()
    waiting_code = State()

user_sessions = {}

# ===== SMS KOD YUBORISH =====
async def send_code(phone: str):
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/vote/send-code/"
        payload = {"phone": phone, "application": APPLICATION_ID}
        headers = {"Content-Type": "application/json"}
        async with session.post(url, json=payload, headers=headers) as resp:
            return await resp.json()

# ===== OVOZ BERISH =====
async def vote(token: str, code: str):
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/vote/confirm/"
        payload = {"token": token, "code": code}
        headers = {"Content-Type": "application/json"}
        async with session.post(url, json=payload, headers=headers) as resp:
            return await resp.json()

# ===== /start =====
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    text = (
        "👋 Salom!\n\n"
        "🗳 Bu bot <b>Beshkapa MFY</b> elektr ta'minoti loyihasiga\n"
        "avtomatik ovoz berish uchun.\n\n"
        "📱 Telefon raqamingizni yuboring:\n"
        "<code>998XXXXXXXXX</code>"
    )
    await message.answer(text, parse_mode="HTML")
    await state.set_state(VoteState.waiting_phone)

# ===== TELEFON RAQAM =====
@dp.message(VoteState.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip().replace("+", "").replace(" ", "")

    if not phone.startswith("998") or len(phone) != 12:
        await message.answer(
            "❌ Noto'g'ri format!\nMasalan: <code>998901234567</code>",
            parse_mode="HTML"
        )
        return

    await message.answer("⏳ SMS kod yuborilmoqda...")

    try:
        data = await send_code(phone)

        if data.get('token'):
            user_sessions[message.from_user.id] = {
                'token': data['token'],
                'phone': phone
            }
            await message.answer("✅ SMS kod yuborildi!\n\n🔢 Kodni kiriting:")
            await state.set_state(VoteState.waiting_code)
        else:
            await message.answer(f"❌ Xatolik: {data}\n\nQayta urinib ko'ring /start")
            await state.clear()

    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}\n\n/start bosing")
        await state.clear()

# ===== SMS KOD =====
@dp.message(VoteState.waiting_code)
async def get_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    session = user_sessions.get(message.from_user.id)

    if not session:
        await message.answer("❌ Sessiya topilmadi. /start bosing.")
        await state.clear()
        return

    await message.answer("⏳ Ovoz berilmoqda...")

    try:
        response = await vote(token=session['token'], code=code)

        if response.get('success') or response.get('status') == 'ok':
            await message.answer(
                "🎉 <b>Ovozingiz qabul qilindi!</b>\n\n"
                "✅ Beshkapa MFY elektr ta'minoti loyihasiga\n"
                "muvaffaqiyatli ovoz berdingiz!",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"❌ Ovoz berishda xatolik:\n<code>{response}</code>\n\n"
                "Qayta urinib ko'ring /start",
                parse_mode="HTML"
            )

    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}\n\n/start bosing")

    finally:
        user_sessions.pop(message.from_user.id, None)
        await state.clear()

# ===== ISHGA TUSHIRISH =====
async def main():
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
