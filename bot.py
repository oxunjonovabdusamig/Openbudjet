# pip install aiogram==3.* OpenBudgetAPI -U

import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openbudget import OpenBudget

# ===== SOZLAMALAR =====
BOT_TOKEN = "8696772155:AAF2-imjoVMo2R2rlLQf_-g2wByJ0_1W8M0"
APPLICATION_ID = "19bcec1a-1524-4766-9982-9e81ac77a15e"  # ✅ sizning loyihangiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== HOLATLAR =====
class VoteState(StatesGroup):
    waiting_phone = State()
    waiting_code = State()

user_sessions = {}

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
        await message.answer("❌ Noto'g'ri format!\nMasalan: <code>998901234567</code>", parse_mode="HTML")
        return

    await message.answer("⏳ SMS kod yuborilmoqda...")

    try:
        ob = OpenBudget(phone=phone, application=APPLICATION_ID)
        data = await ob.send_code()

        if data.get('token'):
            user_sessions[message.from_user.id] = {
                'ob': ob,
                'token': data['token'],
                'phone': phone
            }
            await message.answer(
                "✅ SMS kod yuborildi!\n\n"
                "🔢 Kodni kiriting:"
            )
            await state.set_state(VoteState.waiting_code)
        else:
            await ob.close()
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
        ob = session['ob']
        token = session['token']
        response = await ob.vote(token=token, code=code)

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
        try:
            await session['ob'].close()
        except:
            pass
        user_sessions.pop(message.from_user.id, None)
        await state.clear()

# ===== ISHGA TUSHIRISH =====
async def main():
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
