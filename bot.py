import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, BigInteger, select

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNEL_1 = os.getenv("CHANNEL_1")
CHANNEL_2 = os.getenv("CHANNEL_2")
CHANNEL_1_ID = os.getenv("CHANNEL_1_ID")
CHANNEL_2_ID = os.getenv("CHANNEL_2_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(String, default="Basic")
    has_access: Mapped[bool] = mapped_column(default=False)
    balance: Mapped[float] = mapped_column(default=0.0)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_user(session, user_id):
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(session, user_id):
    user = User(id=user_id)
    session.add(user)
    await session.commit()
    return user

async def update_role(session, user_id, role):
    user = await get_user(session, user_id)
    if user:
        user.role = role
        await session.commit()

async def grant_access(session, user_id):
    user = await get_user(session, user_id)
    if not user:
        user = await create_user(session, user_id)
    user.has_access = True
    await session.commit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def main_menu_kb(role):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить лайк", callback_data="add_like"),
            InlineKeyboardButton(text="💸 Вывести средства", callback_data="withdraw")
        ]
    ])

def subscribe_kb(not_subscribed):
    buttons = []
    if "1" in not_subscribed:
        buttons.append(InlineKeyboardButton(text="Подписаться", url=CHANNEL_1))
    if "2" in not_subscribed:
        buttons.append(InlineKeyboardButton(text="Подписаться", url=CHANNEL_2))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

async def check_subscriptions(user_id):
    not_sub = []
    try:
        member1 = await bot.get_chat_member(CHANNEL_1_ID, user_id)
        if member1.status == "left":
            not_sub.append("1")
    except:
        not_sub.append("1")
    try:
        member2 = await bot.get_chat_member(CHANNEL_2_ID, user_id)
        if member2.status == "left":
            not_sub.append("2")
    except:
        not_sub.append("2")
    return not_sub

@dp.message(Command("start"))
async def start(msg: types.Message):
    async with async_session() as session:
        user = await get_user(session, msg.from_user.id)
        if not user or not user.has_access:
            await msg.answer("❌ Доступ запрещен\nНапишите в тех-поддержку по контакту @sapen800 для получение инструкции о использовании бота.")
            return

        not_sub = await check_subscriptions(msg.from_user.id)
        if not_sub:
            await msg.answer(
                "Для использования данного сервиса вам необходимо подписаться на информационные продукты.",
                reply_markup=subscribe_kb(not_sub)
            )
            return

        await msg.answer(
            f"Добро пожаловать в сервис по приему лайков на ваши сервисы\nВаша роль: {user.role}",
            reply_markup=main_menu_kb(user.role)
        )

@dp.callback_query(F.data == "check_sub")
async def check_sub(call: types.CallbackQuery):
    not_sub = await check_subscriptions(call.from_user.id)
    if not_sub:
        await call.answer("Вы подписаны не на все каналы!", show_alert=True)
        return

    await call.message.delete()
    async with async_session() as session:
        user = await get_user(session, call.from_user.id)
        await call.message.answer(
            f"Добро пожаловать в сервис по приему лайков на ваши сервисы\nВаша роль: {user.role}",
            reply_markup=main_menu_kb(user.role)
        )

@dp.message(Command("grant"))
async def grant(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    try:
        user_id = int(msg.text.split()[1])
        async with async_session() as session:
            await grant_access(session, user_id)
        await msg.answer(f"Доступ выдан пользователю {user_id}")
    except:
        await msg.answer("Использование: /grant user_id")

@dp.message(Command("setrole"))
async def setrole(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    try:
        parts = msg.text.split()
        user_id = int(parts[1])
        role = parts[2]
        if role not in ["Basic", "Standard", "VIP"]:
            await msg.answer("Роли: Basic, Standard, VIP")
            return
        async with async_session() as session:
            await update_role(session, user_id, role)
        await msg.answer(f"Роль {role} установлена пользователю {user_id}")
    except:
        await msg.answer("Использование: /setrole user_id role")

@dp.callback_query(F.data == "add_like")
async def add_like(call: types.CallbackQuery):
    await call.answer("В разработке")

@dp.callback_query(F.data == "withdraw")
async def withdraw(call: types.CallbackQuery):
    await call.answer("В разработке")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
