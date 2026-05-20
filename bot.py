import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Твой реальный Telegram ID
ADMIN_ID = 5249699730

kb_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 Получить консультацию")],
        [KeyboardButton(text="📦 Каталог товаров")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Выберите действие:", reply_markup=kb_main)

@dp.message()
async def handle_all(message: types.Message):
    if message.text == "💬 Получить консультацию":
        await message.answer(
            "Отлично! Напишите в одном сообщении:\n👤 Имя\n📱 Телефон или @telegram\n💬 Кратко, по какому вопросу нужна консультация",
            reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "📦 Каталог товаров":
        catalog = (
            "📦 Наш каталог:\n\n"
            "1️⃣ Летные костюмы (модели: Авиатор, Классик, Профи)\n"
            "2️⃣ Шлемы и защитная экипировка\n"
            "3️⃣ Индивидуальный пошив и доработка\n\n"
            "Чтобы узнать размеры, цены или заказать, нажмите 'Получить консультацию'."
        )
        await message.answer(catalog, reply_markup=kb_main)
    else:
        # Ответ клиенту
        await message.answer(f"✅ Заявка принята!\n\nМы получили:\n{message.text}\n\nСпециалист свяжется с вами в ближайшее время. Для возврата в меню нажмите /start", reply_markup=kb_main)
        # Уведомление владельцу
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 Новая заявка!\n\n👤 Текст: {message.text}\n🆔 ID клиента: {message.from_user.id}\n📱 Юзернейм: @{message.from_user.username or 'не указан'}"
            )
        except Exception:
            pass

async def main():
    print("✅ Бот запущен: уведомления приходят на твой ID. Не закрывай окно.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
