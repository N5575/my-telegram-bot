import asyncio
import os
import json
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMIN_ID = 5249699730

# Загрузка каталога
def load_catalog():
    try:
        with open("catalog.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

catalog = load_catalog()

# ===== КЛАВИАТУРЫ =====

kb_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Связаться с нами")],
        [KeyboardButton(text="О бренде")],
        [KeyboardButton(text="Коллекция")]
    ],
    resize_keyboard=True
)

kb_back = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="go_to_main")]
    ]
)

kb_collection = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Открыть каталог", callback_data="open_catalog")],
        [InlineKeyboardButton(text="Оставить заявку", callback_data="request_consultation")],
        [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="go_to_main")]
    ]
)

# ===== ФУНКЦИИ ПОСТРОЕНИЯ МЕНЮ КАТАЛОГА =====

def get_categories_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Professional", callback_data="category_professional")
    builder.button(text="Pro Fashion", callback_data="category_pro_fashion")
    builder.button(text="🔙 Назад", callback_data="go_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_pro_fashion_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Толстовки", callback_data="subcategory_hoodies")
    builder.button(text="Штаны и брюки", callback_data="subcategory_pants")
    builder.button(text="Футболки и Поло", callback_data="subcategory_tshirts")
    builder.button(text="🔙 Назад", callback_data="open_catalog")
    builder.adjust(1)
    return builder.as_markup()

def get_items_list(subcategory_key):
    builder = InlineKeyboardBuilder()
    subcats = catalog['categories']['pro_fashion']['subcategories']
    items = subcats[subcategory_key]['items']
    for item_key, item_data in items.items():
        builder.button(text=item_data['name'], callback_data=f"item_{item_key}")
    builder.button(text="🔙 Назад", callback_data="category_pro_fashion")
    builder.adjust(1)
    return builder.as_markup()

def get_professional_items_menu():
    builder = InlineKeyboardBuilder()
    items = catalog['categories']['professional']['items']
    for item_key, item_data in items.items():
        builder.button(text=item_data['name'], callback_data=f"prof_item_{item_key}")
    builder.button(text="🔙 Назад", callback_data="open_catalog")
    builder.adjust(1)
    return builder.as_markup()

def get_variant_buttons(item_key, item_data, prefix="item"):
    builder = InlineKeyboardBuilder()
    variants = item_data['variants']
    for var_key, var_data in variants.items():
        color = var_data.get('color', '')
        if item_data.get('has_prints'):
            builder.button(text=color, callback_data=f"prints_{prefix}_{item_key}_{var_key}")
        else:
            builder.button(text=color, callback_data=f"show_{var_key}")
    if prefix == "prof_item":
        builder.button(text="🔙 Назад", callback_data="category_professional")
    else:
        subcat = get_subcategory_by_item(item_key)
        if subcat:
            builder.button(text="🔙 Назад", callback_data=f"subcategory_{subcat}")
    builder.adjust(1)
    return builder.as_markup()

def get_prints_menu(item_key, variant_key, prints):
    builder = InlineKeyboardBuilder()
    for print_name in prints:
        article = f"{variant_key}_{print_name}"
        builder.button(text=print_name, callback_data=f"show_{article}")
    builder.button(text="🔙 Назад", callback_data=f"variant_{item_key}_{variant_key}")
    builder.adjust(2)
    return builder.as_markup()

def get_subcategory_by_item(item_key):
    for subcat_key, subcat_data in catalog['categories']['pro_fashion']['subcategories'].items():
        if item_key in subcat_data['items']:
            return subcat_key
    return None

def find_variant(article):
    """Ищет вариант товара по артикулу во всём каталоге"""
    # Сначала ищем точное совпадение (для товаров без принтов)
    for item_key, item_data in catalog['categories']['professional']['items'].items():
        if article in item_data['variants']:
            return item_data, item_data['variants'][article], "professional", None
    for subcat in catalog['categories']['pro_fashion']['subcategories'].values():
        for item_key, item_data in subcat['items'].items():
            if article in item_data['variants']:
                return item_data, item_data['variants'][article], "pro_fashion", None

    # Если не нашли — пробуем разделить на базовый артикул + принт
    # Например: RA100309G_Kobra -> RA100309G + Kobra
    # Или: RA300100G_AN2 -> RA300100G + AN2
    parts = article.split("_")
    if len(parts) >= 2:
        # Пробуем разные варианты разделения
        for i in range(1, len(parts)):
            base_article = "_".join(parts[:i])
            print_name = "_".join(parts[i:])
            for item_key, item_data in catalog['categories']['professional']['items'].items():
                if base_article in item_data['variants']:
                    return item_data, item_data['variants'][base_article], "professional", print_name
            for subcat in catalog['categories']['pro_fashion']['subcategories'].values():
                for item_key, item_data in subcat['items'].items():
                    if base_article in item_data['variants']:
                        return item_data, item_data['variants'][base_article], "pro_fashion", print_name

    return None, None, None, None

# ===== ОБРАБОТЧИКИ =====

@dp.message(Command("start"))
async def cmd_start(message):
    await message.answer(
        "Добро пожаловать в официальный бот бренда 55.75°\n\n"
        "Здесь вы первыми узнаете о наших новых коллекциях, специальных предложениях и эксклюзивных акциях для подписчиков.\n\n"
        "Если у вас возникнут вопросы или предложения, свяжитесь с нами, оставив заявку обратной связи.",
        reply_markup=kb_main
    )

@dp.callback_query(F.data == "go_to_main")
async def go_to_main(callback):
    await callback.message.answer(
        "Добро пожаловать в официальный бот бренда 55.75°\n\n"
        "Здесь вы первыми узнаете о наших новых коллекциях, специальных предложениях и эксклюзивных акциях для подписчиков.\n\n"
        "Если у вас возникнут вопросы или предложения, свяжитесь с нами, оставив заявку обратной связи.",
        reply_markup=kb_main
    )
    await callback.answer()

@dp.callback_query(F.data == "request_consultation")
async def request_consultation(callback):
    await callback.message.answer(
        "Отлично! Напишите в одном сообщении:\n👤 Имя\n📱 Телефон или @telegram\n💬 Кратко, по какому вопросу нужна консультация",
        reply_markup=kb_back
    )
    await callback.answer()

@dp.callback_query(F.data == "open_catalog")
async def open_catalog(callback):
    await callback.message.edit_text(
        "📂 <b>Каталог коллекции</b>\n\nВыберите категорию:",
        reply_markup=get_categories_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "category_professional")
async def category_professional(callback):
    category = catalog['categories']['professional']
    text = (
        f"👨‍✈️ <b>{category['name']}</b>\n\n"
        "Прямое наследие John Douglas: проверенные временем модели, "
        "доработанные по крою, тканям и фурнитуре.\n\n"
        "Выберите модель:"
    )
    await callback.message.edit_text(text, reply_markup=get_professional_items_menu(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "category_pro_fashion")
async def category_pro_fashion(callback):
    await callback.message.edit_text(
        "🔥 <b>Pro Fashion</b>\n\n"
        "Одежда, в которой комфортно и в полете, и в повседневной жизни.\n\n"
        "Выберите подкатегорию:",
        reply_markup=get_pro_fashion_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("subcategory_"))
async def subcategory_handler(callback):
    subcat_key = callback.data.split("_")[1]
    subcat = catalog['categories']['pro_fashion']['subcategories'][subcat_key]
    await callback.message.edit_text(
        f"📦 <b>{subcat['name']}</b>\n\nВыберите товар:",
        reply_markup=get_items_list(subcat_key),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("prof_item_"))
async def prof_item_handler(callback):
    item_key = callback.data.replace("prof_item_", "")
    item_data = catalog['categories']['professional']['items'][item_key]
    text = f"👨‍✈️ <b>{item_data['name']}</b>\n\nВыберите цвет:"
    await callback.message.edit_text(
        text,
        reply_markup=get_variant_buttons(item_key, item_data, prefix="prof_item"),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("item_"))
async def item_handler(callback):
    item_key = callback.data.replace("item_", "")
    subcats = catalog['categories']['pro_fashion']['subcategories']
    item_data = None
    for subcat in subcats.values():
        if item_key in subcat['items']:
            item_data = subcat['items'][item_key]
            break
    if not item_data:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    text = f"🔥 <b>{item_data['name']}</b>"
    if item_data.get('description'):
        text += f"\n\n{item_data['description']}"
    text += "\n\nВыберите цвет:"
    preview_photos = item_data.get('preview_photos', [])
    if preview_photos:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await bot.send_media_group(
                chat_id=callback.message.chat.id,
                media=[InputMediaPhoto(media=photo_url) for photo_url in preview_photos]
            )
        except Exception as error:
            print(f"Preview photos failed for {item_key}: {error}")
        await callback.message.answer(text, reply_markup=get_variant_buttons(item_key, item_data), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=get_variant_buttons(item_key, item_data), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("prints_"))
async def prints_handler(callback):
    parts = callback.data.split("_")
    if parts[1] == "item":
        item_key = parts[2]
        variant_key = parts[3]
    else:
        item_key = parts[3]
        variant_key = parts[4]

    item_data, _, _, _ = find_variant(variant_key)
    if not item_data:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"🎨 <b>Выберите принт:</b>",
        reply_markup=get_prints_menu(item_key, variant_key, item_data['prints']),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("variant_"))
async def variant_back(callback):
    parts = callback.data.split("_")
    item_key = parts[1]
    item_data, _, source, _ = find_variant(item_key)
    if not item_data:
        await callback.answer("❌ Не найдено", show_alert=True)
        return
    prefix = "prof_item" if source == "professional" else "item"
    text = f"<b>{item_data['name']}</b>\n\nВыберите цвет:"
    await callback.message.edit_text(
        text,
        reply_markup=get_variant_buttons(item_key, item_data, prefix=prefix),
        parse_mode="HTML"
    )
    await callback.answer()

async def show_item_by_article(callback: types.CallbackQuery, article: str):
    if not article:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return False

    item_data, variant, source, print_name = find_variant(article)

    if not item_data:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return False

    emoji = "👨‍✈️" if source == "professional" else "🔥"
    text = f"{emoji} <b>{item_data['name']}</b>\n\n"
    text += f"<b>Артикул:</b> {article}\n"
    text += f"<b>Цвет:</b> {variant.get('color', '')}\n"
    
    if 'composition' in item_data:
        text += f"<b>Состав:</b> {item_data['composition']}\n"
    
    if 'density' in item_data:
        text += f"<b>Плотность:</b> {item_data['density']}\n"
    
    description = variant.get('description') or item_data.get('description')
    if description:
        text += f"\n{description}\n"
    
    if 'price' in item_data:
        text += f"\n<b>Цена:</b> {item_data['price']:,} руб.\n"

    if print_name:
        text += f"\n<b>Принт:</b> {print_name}"

    cross_sell = variant.get('cross_sell') or item_data.get('cross_sell', [])
    if cross_sell:
        text += "\n\n<b>С чем носить:</b>"

    photos_data = variant.get('photos', [])
    photos = []

    if isinstance(photos_data, dict):
        if 'front' in photos_data and photos_data['front']:
            photos.append(photos_data['front'])
        if 'inside' in photos_data and photos_data['inside']:
            photos.append(photos_data['inside'])
        if 'main' in photos_data and photos_data['main']:
            photos.append(photos_data['main'])
        if 'variant' in photos_data and photos_data['variant']:
            photos.append(photos_data['variant'])
        if 'logo' in photos_data and photos_data['logo']:
            photos.append(photos_data['logo'])
        if print_name and print_name in photos_data and photos_data[print_name]:
            photos.append(photos_data[print_name])
    elif isinstance(photos_data, list):
        photos = [p for p in photos_data if p]

    chat_id = callback.message.chat.id
    
    # Создаём кнопки "Оставить заявку" и "Назад"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard_rows = []
    for related_item in cross_sell:
        keyboard_rows.append([
            InlineKeyboardButton(
                text=related_item["text"],
                callback_data=related_item["callback_data"]
            )
        ])
    keyboard_rows.append([InlineKeyboardButton(text="Оставить заявку", callback_data=f"order_{article}")])
    keyboard_rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="go_back_to_colors")])
    order_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    if photos:
        # Отправляем все фото БЕЗ кнопок, кроме последнего
        for photo_url in photos[:-1]:
            await bot.send_photo(chat_id=chat_id, photo=photo_url)
        # Последнее фото — с текстом и кнопками
        await bot.send_photo(chat_id=chat_id, photo=photos[-1], caption=text, parse_mode="HTML", reply_markup=order_keyboard)
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=order_keyboard)

    return True

@dp.callback_query(F.data.startswith("show_"))
async def show_item(callback: types.CallbackQuery):
    article = callback.data.replace("show_", "")
    if await show_item_by_article(callback, article):
        await callback.answer()

# ===== ТЕКСТОВЫЕ СООБЩЕНИЯ =====

@dp.message(StateFilter(None))
async def handle_all(message):
    if message.text == "Связаться с нами":
        await message.answer(
            "Отлично! Напишите в одном сообщении:\n👤 Имя\n📱 Телефон или @telegram\n💬 Кратко, по какому вопросу нужна консультация",
            reply_markup=kb_back
        )
    elif message.text == "О бренде":
        text = (
            "📖 О бренде 55.75°:\n\n"
            "55.75° — не просто цифры. Это точная географическая широта, которая проходит через всю территорию России. От западных рубежей через древние города, через бескрайние просторы Сибири до суровых берегов Тихого океана.\n\n"
            "Этот градус — не линия на карте, это нить судьбы, связывающая воедино культуру, климат и характер огромной страны.\n\n"
            "Почему широта, а не долгота?\n"
            "Потому что широта диктует климат. А климат диктует стиль жизни. Мы создаем одежду для тех, кто понимает ценность тепла в условиях холода и ценность свободы на просторах территории.\n\n"
            "Наш бренд создан для людей, влюбленных в небо. Наша миссия — сделать профессиональную одежду для полетов максимально комфортной, а эстетику профессиональной экипировки перенести в повседневную жизнь.\n\n"
            'Наша одежда создана <a href="https://t.me/nezhdana_jet">пилотом</a> и для пилотов. Мы производим одежду в России и для России.'
        )
        await message.answer(text, reply_markup=kb_back, parse_mode="HTML")
    elif message.text == "Коллекция":
        text = (
            "👗 В нашей новой коллекции два направления: Professional и Pro Fashion.\n\n"
            "Professional - это прямое наследие John Douglas: проверенные временем модели, которые мы доработали по крою, тканям и фурнитуре.\n\n"
            "Pro Fashion - одежда, в которой комфортно и в полете и в повседневной жизни. Принты, нашивки и шевроны - не просто декор, а визуальный маркер принадлежности к авиации.\n"
            "В линейке: три модели брюк, три модели толстовок, футболки и поло.\n\n"
            "Элементы коллекции легко комбинируются между собой и подобраны таким образом, чтобы из них можно было собрать образ под любую задачу.\n\n"
            "Нашим главным приоритетом является качество и внимание к деталям. Мы используем только натуральные ткани, и ткани с пропитками, если это диктует функционал вещи.\n"
            "Тщательнейшим образом отбираем фурнитуру. Используем инновационные технологии нанесения принтов.\n\n"
            "Наша задача - чтобы вещи бренда служили долго и безотказно, выделяли владельца из толпы и создавали комфорт в полетах и повседневной жизни.\n\n"
            "Вы можете оставить заявку и мы расскажем вам о коллекции подробнее"
        )
        await message.answer(text, reply_markup=kb_collection)
    else:
        await message.answer(
            f"✅ Заявка принята!\n\nМы получили:\n{message.text}\n\nСпециалист свяжется с вами в ближайшее время.",
            reply_markup=kb_back
        )
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 Новая заявка!\n\n👤 Текст: {message.text}\n🆔 ID клиента: {message.from_user.id}\n📱 Юзернейм: @{message.from_user.username or 'не указан'}"
            )
        except Exception:
            pass



class OrderForm(StatesGroup):
    waiting_for_size = State()
    waiting_for_contacts = State()




@dp.callback_query(F.data.startswith("order_"))
async def order_handler(callback: types.CallbackQuery, state: FSMContext):
    article = callback.data.replace("order_", "")
    
    # Определяем подкатегорию товара
    item_data, variant, source, print_name = find_variant(article)
    item_name = item_data.get('name', '').lower() if item_data else ''
    # Все штаны, брюки, джоггеры = бедра, остальное = грудь
    if any(word in item_name for word in ['штаны', 'брюки', 'джоггеры', 'карго']):
        subcategory = "pants"
    else:
        subcategory = "other"
    
    await state.update_data(article=article, subcategory=subcategory, print_name=print_name)
    
    await callback.message.answer(
        "📏 <b>Выберите размер:</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="48", callback_data="size_48")],
                [InlineKeyboardButton(text="50", callback_data="size_50")],
                [InlineKeyboardButton(text="52", callback_data="size_52")],
                [InlineKeyboardButton(text="54", callback_data="size_54")],
                [InlineKeyboardButton(text="🤔 Помочь определить размер", callback_data="help_size")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_item")]
            ]
        ),
        parse_mode="HTML"
    )
    await callback.answer()
    await state.set_state(OrderForm.waiting_for_size)


@dp.callback_query(F.data == "help_size")
async def help_size(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    subcategory = data.get('subcategory', 'other')
    
    if subcategory == "pants":
        size_table = "📏 <b>Таблица размеров (брюки):</b>\n\n48 — обхват бедер 100-103 см\n50 — обхват бедер 103-106 см\n52 — обхват бедер 106-109 см\n54 — обхват бедер 109-112 см"
    else:
        size_table = "📏 <b>Таблица размеров:</b>\n\n48 — обхват груди 96 см\n50 — обхват груди 100 см\n52 — обхват груди 104 см\n54 — обхват груди 108 см"
    
    await callback.message.edit_text(
        f"{size_table}\n\nЕсли нужна помощь — напишите нам: @N5575_support",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Выбрать размер", callback_data="back_to_sizes")]
            ]
        ),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_sizes")
async def back_to_sizes(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📏 <b>Выберите размер:</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="48", callback_data="size_48")],
                [InlineKeyboardButton(text="50", callback_data="size_50")],
                [InlineKeyboardButton(text="52", callback_data="size_52")],
                [InlineKeyboardButton(text="54", callback_data="size_54")],
                [InlineKeyboardButton(text="🤔 Помочь определить размер", callback_data="help_size")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_item")]
            ]
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("size_"))
async def size_selected(callback: types.CallbackQuery, state: FSMContext):
    size = callback.data.replace("size_", "")
    print(f"DEBUG: Выбран размер {size}")
    await state.update_data(size=size)
    print(f"DEBUG: Размер сохранён в state")
    
    await callback.answer()
    
    await callback.message.edit_text(
        "👤 <b>Напишите ваше имя и контакты одним сообщением:</b>",
        parse_mode="HTML"
    )
    await state.set_state(OrderForm.waiting_for_contacts)
    print(f"DEBUG: Состояние установлено на waiting_for_contacts")


@dp.callback_query(F.data == "back_to_item")
async def back_to_item(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    article = data.get("article")
    
    await state.clear()
    
    # Возвращаемся к карточке товара
    if await show_item_by_article(callback, article):
        await callback.answer()


@dp.message(OrderForm.waiting_for_contacts)
async def contacts_received(message: types.Message, state: FSMContext):
    print(f"DEBUG contacts_received: Введены контакты {message.text}")
    await state.update_data(contacts=message.text)
    data = await state.get_data()
    print(f"DEBUG contacts_received: data = {data}")
    
    order_text = "🛒 <b>НОВАЯ ЗАЯВКА</b>\n\n"
    order_text += f"📦 Артикул: {data.get('article')}\n"
    if data.get('print_name'):
        order_text += f"🎨 Принт: {data.get('print_name')}\n"
    order_text += f"📏 Размер: {data.get('size')}\n"
    order_text += f"👤 Контакты: {data.get('contacts')}\n"
    
    await message.answer(
        "✅ <b>Заявка отправлена!</b>\n\nМы свяжемся с вами в ближайшее время.",
        parse_mode="HTML"
    )
    
    ADMIN_ID = 5249699730
    try:
        await bot.send_message(ADMIN_ID, order_text, parse_mode="HTML")
    except:
        pass
    
    await state.clear()

@dp.callback_query(F.data == "go_back_to_colors")
async def go_back_to_colors(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔙 Выберите товар:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В каталог", callback_data="open_catalog")]
            ]
        )
    )
    await callback.answer()


async def main():
    print("✅ Бот запущен на сервере!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
