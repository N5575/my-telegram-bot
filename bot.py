import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

ADMIN_ID = 5249699730

kb_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 Получить консультацию")],
        [KeyboardButton(text="📦 Каталог товаров")],
        [KeyboardButton(text="📖 О бренде")]
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
            "🔹 Серия PRO FASHION:\n"
            "• Толстовки\n"
            "• Брюки\n"
            "• Футболки\n\n"
            "🔹 Серия PROFESSIONAL:\n"
            "• Летные костюмы\n"
            "• Комбинезоны\n\n"
            "📝 Оставьте заявку, мы оповестим, когда продукция будет готова к предзаказу."
        )
        await message.answer(catalog, reply_markup=kb_main)
    elif message.text == "📖 О бренде":
        await message.answer(
            "📖 О бренде 55.75°:\n\n"
            "55.75° — не просто цифры. Это точная географическая широта, которая проходит через всю территорию России. От западных рубежей через древние города, через бескрайние просторы Сибири до суровых берегов Тихого океана.\n\n"
            "Этот градус — не линия на карте, это нить судьбы, связывающая воедино культуру, климат и характер огромной страны.\n\n"
            "Почему широта, а не долгота?\n"
            "Потому что широта диктует климат. А климат диктует стиль жизни. Мы создаем одежду для тех, кто понимает ценность тепла в условиях холода и ценность свободы на просторах территории.",
            reply_markup=kb_main
        )
    else:
        await message.answer(f"✅ Заявка принята!\n\nМы получили:\n{message.text}\n\nСпециалист свяжется с вами в ближайшее время. Для возврата в меню нажмите /start", reply_markup=kb_main)
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 Новая заявка!\n\n👤 Текст: {message.text}\n🆔 ID клиента: {message.from_user.id}\n📱 Юзернейм: @{message.from_user.username or 'не указан'}"
            )
        except Exception:
            pass

async def main():
    print("✅ Бот запущен на сервере!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
