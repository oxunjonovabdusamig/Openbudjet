import asyncio
import os
import logging
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncpg

# ===== LOGGING =====

logging.basicConfig(
level=logging.INFO,
format=”%(asctime)s [%(levelname)s] %(message)s”,
handlers=[
logging.StreamHandler()
]
)
logger = logging.getLogger(**name**)

# ===== SOZLAMALAR =====

BOT_TOKEN = os.getenv(“BOT_TOKEN”)
ADMIN_IDS = list(map(int, os.getenv(“ADMIN_IDS”, “0”).split(”,”)))
DATABASE_URL = os.getenv(“DATABASE_URL”)
APPLICATION_ID = “19bcec1a-1524-4766-9982-9e81ac77a15e”
BASE_URL = “https://openbudget.uz/api”

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool = None

# ===== DATABASE =====

async def init_db():
global db_pool
db_pool = await asyncpg.create_pool(DATABASE_URL)
async with db_pool.acquire() as conn:
await conn.execute(”””
CREATE TABLE IF NOT EXISTS users (
id BIGSERIAL PRIMARY KEY,
telegram_id BIGINT UNIQUE NOT NULL,
username TEXT,
full_name TEXT,
phone TEXT,
voted BOOLEAN DEFAULT FALSE,
voted_at TIMESTAMP,
created_at TIMESTAMP DEFAULT NOW()
)
“””)
await conn.execute(”””
CREATE TABLE IF NOT EXISTS vote_logs (
id BIGSERIAL PRIMARY KEY,
telegram_id BIGINT,
phone TEXT,
status TEXT,
response TEXT,
created_at TIMESTAMP DEFAULT NOW()
)
“””)
logger.info(“Database initialized!”)

async def get_or_create_user(telegram_id, username, full_name):
async with db_pool.acquire() as conn:
user = await conn.fetchrow(
“SELECT * FROM users WHERE telegram_id = $1”, telegram_id
)
if not user:
await conn.execute(
“INSERT INTO users (telegram_id, username, full_name) VALUES ($1, $2, $3)”,
telegram_id, username, full_name
)
logger.info(f”New user: {telegram_id} - {full_name}”)
return user

async def update_user_voted(telegram_id, phone):
async with db_pool.acquire() as conn:
await conn.execute(
“UPDATE users SET voted=TRUE, voted_at=NOW(), phone=$1 WHERE telegram_id=$2”,
phone, telegram_id
)

async def log_vote(telegram_id, phone, status, response):
async with db_pool.acquire() as conn:
await conn.execute(
“INSERT INTO vote_logs (telegram_id, phone, status, response) VALUES ($1, $2, $3, $4)”,
telegram_id, phone, status, str(response)
)

async def get_stats():
async with db_pool.acquire() as conn:
total = await conn.fetchval(“SELECT COUNT(*) FROM users”)
voted = await conn.fetchval(“SELECT COUNT(*) FROM users WHERE voted=TRUE”)
today = await conn.fetchval(
“SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE”
)
last_votes = await conn.fetch(
“SELECT full_name, phone, voted_at FROM users WHERE voted=TRUE ORDER BY voted_at DESC LIMIT 5”
)
return total, voted, today, last_votes

# ===== OPENBUDGET API =====

async def send_code(phone: str):
try:
async with aiohttp.ClientSession() as session:
url = f”{BASE_URL}/vote/send-code/”
payload = {“phone”: phone, “application”: APPLICATION_ID}
headers = {“Content-Type”: “application/json”}
async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
data = await resp.json()
logger.info(f”send_code [{phone}]: {data}”)
return data
except Exception as e:
logger.error(f”send_code error: {e}”)
return {}

async def vote_request(token: str, code: str):
try:
async with aiohttp.ClientSession() as session:
url = f”{BASE_URL}/vote/confirm/”
payload = {“token”: token, “code”: code}
headers = {“Content-Type”: “application/json”}
async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
data = await resp.json()
logger.info(f”vote_request: {data}”)
return data
except Exception as e:
logger.error(f”vote_request error: {e}”)
return {}

# ===== FSM STATES =====

class VoteState(StatesGroup):
waiting_phone = State()
waiting_code = State()

user_sessions = {}

# ===== KEYBOARDS =====

def main_menu():
return InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=“✅ Ovoz berish”, callback_data=“start_vote”)],
[InlineKeyboardButton(text=“ℹ️ Loyiha haqida”, callback_data=“about”)]
])

def cancel_kb():
return InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=“❌ Bekor qilish”, callback_data=“cancel”)]
])

def admin_menu():
return InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=“📊 Statistika”, callback_data=“admin_stats”)],
[InlineKeyboardButton(text=“👥 Foydalanuvchilar”, callback_data=“admin_users”)],
[InlineKeyboardButton(text=“📢 Xabar yuborish”, callback_data=“admin_broadcast”)]
])

# ===== HANDLERS =====

@dp.message(Command(“start”))
async def start(message: types.Message, state: FSMContext):
await state.clear()
await get_or_create_user(
message.from_user.id,
message.from_user.username,
message.from_user.full_name
)
text = (
“Salom, <b>{}</b>!\n\n”
“Bu bot <b>Beshkapa MFY</b> elektr taminoti loyihasiga\n”
“ovoz berish uchun yaratilgan.\n\n”
“Loyiha: Beshkapa MFY aholisining elektr taminotini yaxshilash\n”
“ID: 053461111011\n\n”
“Boshlash uchun quyidagi tugmani bosing:”
).format(message.from_user.first_name)
await message.answer(text, parse_mode=“HTML”, reply_markup=main_menu())

@dp.callback_query(F.data == “about”)
async def about(call: types.CallbackQuery):
text = (
“Loyiha haqida:\n\n”
“Nom: Elektr energiyasi taminoti bilan bogliq tadbirlar\n”
“ID: 053461111011\n”
“Tur: Qurilish va tamirash\n”
“Viloyat: Fargona viloyati, Ozbekiston tumani\n”
“MFY: Beshkapa\n\n”
“Maqsad: TP va tayanchilar ornatis hamda tarmoq tortish”
)
await call.message.edit_text(text, reply_markup=main_menu())
await call.answer()

@dp.callback_query(F.data == “cancel”)
async def cancel(call: types.CallbackQuery, state: FSMContext):
await state.clear()
user_sessions.pop(call.from_user.id, None)
await call.message.edit_text(“Bekor qilindi.”, reply_markup=main_menu())
await call.answer()

@dp.callback_query(F.data == “start_vote”)
async def start_vote(call: types.CallbackQuery, state: FSMContext):
await call.message.edit_text(
“Telefon raqamingizni kiriting:\n\n”
“Format: 998901234567\n”
“(+ belgisiz, probelsiz)”,
reply_markup=cancel_kb()
)
await state.set_state(VoteState.waiting_phone)
await call.answer()

@dp.message(VoteState.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
phone = message.text.strip().replace(”+”, “”).replace(” “, “”).replace(”-”, “”)

```
if not phone.startswith("998") or len(phone) != 12 or not phone.isdigit():
    await message.answer(
        "Notogri format!\n\nMasalan: 998901234567",
        reply_markup=cancel_kb()
    )
    return

msg = await message.answer("SMS kod yuborilmoqda...")

data = await send_code(phone)

if data.get("token"):
    user_sessions[message.from_user.id] = {
        "token": data["token"],
        "phone": phone
    }
    await msg.edit_text(
        "SMS kod yuborildi!\n\n"
        "Raqamingizga kelgan 6 xonali kodni kiriting:",
        reply_markup=cancel_kb()
    )
    await state.set_state(VoteState.waiting_code)
else:
    await log_vote(message.from_user.id, phone, "send_code_failed", data)
    await msg.edit_text(
        f"Xatolik yuz berdi.\n\nJavob: {data}\n\nQayta urining:",
        reply_markup=main_menu()
    )
    await state.clear()
```

@dp.message(VoteState.waiting_code)
async def get_code(message: types.Message, state: FSMContext):
code = message.text.strip()
session = user_sessions.get(message.from_user.id)

```
if not session:
    await message.answer("Sessiya topilmadi.", reply_markup=main_menu())
    await state.clear()
    return

if not code.isdigit():
    await message.answer("Faqat raqam kiriting!", reply_markup=cancel_kb())
    return

msg = await message.answer("Ovoz berilmoqda...")

response = await vote_request(token=session["token"], code=code)

if response.get("success") or response.get("status") == "ok":
    await update_user_voted(message.from_user.id, session["phone"])
    await log_vote(message.from_user.id, session["phone"], "success", response)
    await msg.edit_text(
        "Ovozingiz qabul qilindi!\n\n"
        "Beshkapa MFY elektr taminoti loyihasiga\n"
        "muvaffaqiyatli ovoz berdingiz!\n\n"
        "Ishtirokingiz uchun rahmat!"
    )
    logger.info(f"Vote success: {message.from_user.id} - {session['phone']}")
else:
    await log_vote(message.from_user.id, session["phone"], "failed", response)
    await msg.edit_text(
        f"Ovoz berishda xatolik:\n{response}\n\nQayta urining:",
        reply_markup=main_menu()
    )

user_sessions.pop(message.from_user.id, None)
await state.clear()
```

# ===== ADMIN PANEL =====

def is_admin(user_id: int) -> bool:
return user_id in ADMIN_IDS

@dp.message(Command(“admin”))
async def admin_panel(message: types.Message):
if not is_admin(message.from_user.id):
await message.answer(“Ruxsat yoq!”)
return
await message.answer(“Admin panel:”, reply_markup=admin_menu())

@dp.callback_query(F.data == “admin_stats”)
async def admin_stats(call: types.CallbackQuery):
if not is_admin(call.from_user.id):
await call.answer(“Ruxsat yoq!”, show_alert=True)
return

```
total, voted, today, last_votes = await get_stats()

last_text = ""
for v in last_votes:
    voted_time = v["voted_at"].strftime("%d.%m %H:%M") if v["voted_at"] else "-"
    last_text += f"  {v['full_name']} | {v['phone']} | {voted_time}\n"

text = (
    "Statistika:\n\n"
    f"Jami foydalanuvchilar: {total}\n"
    f"Ovoz berganlar: {voted}\n"
    f"Bugun qoshilganlar: {today}\n"
    f"Konversiya: {round(voted/total*100 if total else 0, 1)}%\n\n"
    f"Oxirgi ovozlar:\n{last_text if last_text else 'Yoq'}"
)
await call.message.edit_text(text, reply_markup=admin_menu())
await call.answer()
```

@dp.callback_query(F.data == “admin_users”)
async def admin_users(call: types.CallbackQuery):
if not is_admin(call.from_user.id):
await call.answer(“Ruxsat yoq!”, show_alert=True)
return

```
async with db_pool.acquire() as conn:
    users = await conn.fetch(
        "SELECT full_name, phone, voted, created_at FROM users ORDER BY created_at DESC LIMIT 10"
    )

text = "Oxirgi 10 foydalanuvchi:\n\n"
for u in users:
    status = "Ovoz berdi" if u["voted"] else "Bermadi"
    date = u["created_at"].strftime("%d.%m %H:%M")
    text += f"{u['full_name']} | {status} | {date}\n"

await call.message.edit_text(text, reply_markup=admin_menu())
await call.answer()
```

@dp.callback_query(F.data == “admin_broadcast”)
async def admin_broadcast_start(call: types.CallbackQuery, state: FSMContext):
if not is_admin(call.from_user.id):
await call.answer(“Ruxsat yoq!”, show_alert=True)
return
await call.message.edit_text(“Barcha foydalanuvchilarga yuboriladigan xabarni yozing:”)
await state.set_state(“broadcast”)
await call.answer()

@dp.message(F.text, lambda m: True)
async def broadcast_handler(message: types.Message, state: FSMContext):
current = await state.get_state()
if current != “broadcast” or not is_admin(message.from_user.id):
return

```
async with db_pool.acquire() as conn:
    users = await conn.fetch("SELECT telegram_id FROM users")

sent = 0
failed = 0
for user in users:
    try:
        await bot.send_message(user["telegram_id"], message.text)
        sent += 1
        await asyncio.sleep(0.05)
    except Exception:
        failed += 1

await message.answer(
    f"Xabar yuborildi!\n\nMuvaffaqiyatli: {sent}\nXato: {failed}",
    reply_markup=admin_menu()
)
await state.clear()
```

# ===== MAIN =====

async def main():
logger.info(“Bot ishga tushmoqda…”)
await init_db()
logger.info(“Bot ishga tushdi!”)
await dp.start_polling(bot, skip_updates=True)

if **name** == “**main**”:
asyncio.run(main())
