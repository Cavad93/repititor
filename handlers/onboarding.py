from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from datetime import time as dt_time
import logging

from database.connection import async_session_maker
from database.models import User, UserPreference
from handlers.states import OnboardingStates

logger = logging.getLogger(__name__)

router = Router()

# Константы для категорий товаров
CATEGORIES = [
    ("📱 Электроника", "electronics"),
    ("👕 Одежда и обувь", "clothing"),
    ("💄 Красота и здоровье", "beauty"),
    ("🏠 Товары для дома", "home"),
    ("🍎 Продукты питания", "food"),
    ("⚽ Спорт и отдых", "sports"),
    ("👶 Детские товары", "kids"),
    ("📚 Книги и канцелярия", "books"),
    ("🚗 Автотовары", "auto"),
    ("🐕 Товары для животных", "pets"),
]

# Константы для магазинов
SHOPS = [
    ("Wildberries", "wildberries"),
    ("Ozon", "ozon"),
    ("Яндекс Маркет", "yandex_market"),
    ("СберМегаМаркет", "sber"),
    ("Lamoda", "lamoda"),
    ("М.Видео", "mvideo"),
    ("Детский мир", "detmir"),
    ("Читай-город", "chitai_gorod"),
]

# Ценовые диапазоны
PRICE_RANGES = [
    ("До 1000₽", "0-1000"),
    ("1000-3000₽", "1000-3000"),
    ("3000-10000₽", "3000-10000"),
    ("Больше 10000₽", "10000+"),
    ("Любой", "any"),
]

# Частота уведомлений
NOTIFICATION_FREQ = [
    ("⚡ Мгновенно", "instant"),
    ("📅 Один раз в день", "daily"),
    ("📅 Два раза в день", "twice_daily"),
    ("📅 Три раза в неделю", "three_weekly"),
    ("🔕 Только по запросу", "manual"),
]

# Время уведомлений
NOTIFICATION_TIMES = [
    ("🌅 Утро (9:00)", "09:00"),
    ("☀️ День (13:00)", "13:00"),
    ("🌆 Вечер (18:00)", "18:00"),
    ("🌙 Ночь (21:00)", "21:00"),
]


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    """
    Команда /setup - запуск процесса анкетирования.
    
    Проверяет есть ли у пользователя сохраненные настройки.
    Если есть - предлагает редактировать существующие или начать заново.
    Если нет - сразу запускает анкетирование.
    """
    user_id = message.from_user.id
    
    async with async_session_maker() as session:
        try:
            # Проверяем есть ли уже настройки
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            existing_prefs = result.scalar_one_or_none()
            
            if existing_prefs:
                # У пользователя уже есть настройки
                builder = InlineKeyboardBuilder()
                builder.button(text="✏️ Редактировать настройки", callback_data="onboarding:edit")
                builder.button(text="🔄 Начать заново", callback_data="onboarding:restart")
                builder.button(text="❌ Отмена", callback_data="onboarding:cancel")
                builder.adjust(1)
                
                await message.answer(
                    "⚙️ У тебя уже есть сохраненные настройки персонализации.\n\n"
                    "Что хочешь сделать?",
                    reply_markup=builder.as_markup()
                )
            else:
                # Настроек нет - запускаем анкетирование
                await start_onboarding(message, state)
                
        except Exception as e:
            logger.error(f"Ошибка при запуске /setup для пользователя {user_id}: {e}", exc_info=True)
            await message.answer("Произошла ошибка. Попробуй позже.")


@router.callback_query(F.data == "onboarding:restart")
async def callback_restart_onboarding(callback: CallbackQuery, state: FSMContext):
    """Начать анкетирование заново."""
    await callback.answer()
    await start_onboarding(callback.message, state, is_restart=True)


@router.callback_query(F.data == "onboarding:cancel")
async def callback_cancel_onboarding(callback: CallbackQuery, state: FSMContext):
    """Отмена анкетирования."""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "❌ Настройка отменена.\n\n"
        "Используй /setup чтобы настроить персонализацию в любое время."
    )


async def start_onboarding(message: Message, state: FSMContext, is_restart: bool = False):
    """
    Начало процесса анкетирования - шаг 1: выбор категорий.
    
    Args:
        message: Объект сообщения
        state: FSM контекст для хранения состояния
        is_restart: Флаг перезапуска анкеты
    """
    # Инициализируем пустой словарь для хранения выбранных значений
    await state.update_data(
        selected_categories=[],
        selected_shops=[],
        selected_price_ranges=[],
        notification_frequency=None,
        notification_time=None
    )
    
    await state.set_state(OnboardingStates.categories)
    
    intro_text = (
        "🎯 <b>Персонализация рекомендаций</b>\n\n"
        "Давай настроим бота под твои интересы!\n"
        "Это займет всего пару минут, но сделает твою ленту намного полезнее.\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📋 <b>Шаг 1 из 4: Категории товаров</b>\n\n"
        "Выбери категории, которые тебя интересуют.\n"
        "Можешь выбрать несколько вариантов.\n\n"
        "Выбранные категории будут отмечены ✅"
    )
    
    keyboard = get_categories_keyboard([])
    
    if is_restart:
        await message.edit_text(intro_text, reply_markup=keyboard)
    else:
        await message.answer(intro_text, reply_markup=keyboard)
    
    logger.info(f"Пользователь {message.from_user.id if hasattr(message, 'from_user') else message.chat.id} начал анкетирование")


def get_categories_keyboard(selected: list) -> InlineKeyboardBuilder:
    """
    Создает клавиатуру для выбора категорий с отметками выбранных.
    
    Args:
        selected: Список уже выбранных категорий (их ID)
    
    Returns:
        InlineKeyboardMarkup с кнопками категорий
    """
    builder = InlineKeyboardBuilder()
    
    for name, cat_id in CATEGORIES:
        # Добавляем галочку к выбранным категориям
        checkmark = "✅ " if cat_id in selected else ""
        builder.button(
            text=f"{checkmark}{name}",
            callback_data=f"onb_cat:{cat_id}"
        )
    
    builder.adjust(2)  # 2 кнопки в ряд
    
    # Кнопки навигации
    builder.row(
        InlineKeyboardBuilder().button(
            text="➡️ Далее",
            callback_data="onb:next_from_categories"
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(F.data.startswith("onb_cat:"))
async def callback_toggle_category(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора/отмены категории.
    
    Добавляет или удаляет категорию из списка выбранных
    и обновляет клавиатуру с отметками.
    """
    await callback.answer()
    
    category_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    
    # Переключаем состояние категории
    if category_id in selected:
        selected.remove(category_id)
    else:
        selected.append(category_id)
    
    await state.update_data(selected_categories=selected)
    
    # Обновляем текст с количеством выбранных
    categories_text = (
        "📋 <b>Шаг 1 из 4: Категории товаров</b>\n\n"
        "Выбери категории, которые тебя интересуют.\n"
        "Можешь выбрать несколько вариантов.\n\n"
        f"Выбрано: {len(selected)}\n\n"
        "Выбранные категории будут отмечены ✅"
    )
    
    keyboard = get_categories_keyboard(selected)
    
    try:
        await callback.message.edit_text(categories_text, reply_markup=keyboard)
    except Exception as e:
        # Игнорируем ошибку если сообщение не изменилось
        logger.debug(f"Не удалось обновить сообщение: {e}")


@router.callback_query(F.data == "onb:next_from_categories")
async def callback_next_to_shops(callback: CallbackQuery, state: FSMContext):
    """Переход к шагу 2: выбор магазинов."""
    await callback.answer()
    
    data = await state.get_data()
    selected_categories = data.get("selected_categories", [])
    
    if not selected_categories:
        await callback.answer(
            "⚠️ Выбери хотя бы одну категорию!",
            show_alert=True
        )
        return
    
    await state.set_state(OnboardingStates.shops)
    
    shops_text = (
        "📋 <b>Шаг 2 из 4: Магазины</b>\n\n"
        "Выбери магазины и маркетплейсы, где обычно совершаешь покупки.\n\n"
        "Мы будем показывать тебе предложения именно из этих магазинов.\n\n"
        "Выбрано: 0"
    )
    
    keyboard = get_shops_keyboard([])
    await callback.message.edit_text(shops_text, reply_markup=keyboard)


def get_shops_keyboard(selected: list) -> InlineKeyboardBuilder:
    """Создает клавиатуру для выбора магазинов."""
    builder = InlineKeyboardBuilder()
    
    for name, shop_id in SHOPS:
        checkmark = "✅ " if shop_id in selected else ""
        builder.button(
            text=f"{checkmark}{name}",
            callback_data=f"onb_shop:{shop_id}"
        )
    
    builder.adjust(2)
    
    # Навигация
    builder.row(
        InlineKeyboardBuilder().button(
            text="⬅️ Назад",
            callback_data="onb:back_to_categories"
        ).as_markup().inline_keyboard[0][0],
        InlineKeyboardBuilder().button(
            text="➡️ Далее",
            callback_data="onb:next_from_shops"
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(F.data.startswith("onb_shop:"))
async def callback_toggle_shop(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора/отмены магазина."""
    await callback.answer()
    
    shop_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_shops", [])
    
    if shop_id in selected:
        selected.remove(shop_id)
    else:
        selected.append(shop_id)
    
    await state.update_data(selected_shops=selected)
    
    shops_text = (
        "📋 <b>Шаг 2 из 4: Магазины</b>\n\n"
        "Выбери магазины и маркетплейсы, где обычно совершаешь покупки.\n\n"
        "Мы будем показывать тебе предложения именно из этих магазинов.\n\n"
        f"Выбрано: {len(selected)}"
    )
    
    keyboard = get_shops_keyboard(selected)
    
    try:
        await callback.message.edit_text(shops_text, reply_markup=keyboard)
    except Exception:
        pass


@router.callback_query(F.data == "onb:back_to_categories")
async def callback_back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возврат к шагу 1: категории."""
    await callback.answer()
    await state.set_state(OnboardingStates.categories)
    
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    
    categories_text = (
        "📋 <b>Шаг 1 из 4: Категории товаров</b>\n\n"
        "Выбери категории, которые тебя интересуют.\n"
        "Можешь выбрать несколько вариантов.\n\n"
        f"Выбрано: {len(selected)}\n\n"
        "Выбранные категории будут отмечены ✅"
    )
    
    keyboard = get_categories_keyboard(selected)
    await callback.message.edit_text(categories_text, reply_markup=keyboard)


@router.callback_query(F.data == "onb:next_from_shops")
async def callback_next_to_price(callback: CallbackQuery, state: FSMContext):
    """Переход к шагу 3: ценовой диапазон."""
    await callback.answer()
    
    data = await state.get_data()
    selected_shops = data.get("selected_shops", [])
    
    if not selected_shops:
        await callback.answer(
            "⚠️ Выбери хотя бы один магазин!",
            show_alert=True
        )
        return
    
    await state.set_state(OnboardingStates.price_range)
    
    price_text = (
        "📋 <b>Шаг 3 из 4: Ценовой диапазон</b>\n\n"
        "Укажи в каком ценовом диапазоне ты обычно ищешь товары.\n\n"
        "Можешь выбрать несколько вариантов или 'Любой'.\n\n"
        "Выбрано: 0"
    )
    
    keyboard = get_price_keyboard([])
    await callback.message.edit_text(price_text, reply_markup=keyboard)


def get_price_keyboard(selected: list) -> InlineKeyboardBuilder:
    """Создает клавиатуру для выбора ценового диапазона."""
    builder = InlineKeyboardBuilder()
    
    for name, price_id in PRICE_RANGES:
        checkmark = "✅ " if price_id in selected else ""
        builder.button(
            text=f"{checkmark}{name}",
            callback_data=f"onb_price:{price_id}"
        )
    
    builder.adjust(2)
    
    # Навигация
    builder.row(
        InlineKeyboardBuilder().button(
            text="⬅️ Назад",
            callback_data="onb:back_to_shops"
        ).as_markup().inline_keyboard[0][0],
        InlineKeyboardBuilder().button(
            text="➡️ Далее",
            callback_data="onb:next_from_price"
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(F.data.startswith("onb_price:"))
async def callback_toggle_price(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора ценового диапазона."""
    await callback.answer()
    
    price_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_price_ranges", [])
    
    # Если выбран "Любой" - очищаем остальные выборы
    if price_id == "any":
        selected = ["any"]
    else:
        # Если выбран конкретный диапазон - убираем "Любой"
        if "any" in selected:
            selected.remove("any")
        
        if price_id in selected:
            selected.remove(price_id)
        else:
            selected.append(price_id)
    
    await state.update_data(selected_price_ranges=selected)
    
    price_text = (
        "📋 <b>Шаг 3 из 4: Ценовой диапазон</b>\n\n"
        "Укажи в каком ценовом диапазоне ты обычно ищешь товары.\n\n"
        "Можешь выбрать несколько вариантов или 'Любой'.\n\n"
        f"Выбрано: {len(selected)}"
    )
    
    keyboard = get_price_keyboard(selected)
    
    try:
        await callback.message.edit_text(price_text, reply_markup=keyboard)
    except Exception:
        pass


@router.callback_query(F.data == "onb:back_to_shops")
async def callback_back_to_shops(callback: CallbackQuery, state: FSMContext):
    """Возврат к шагу 2: магазины."""
    await callback.answer()
    await state.set_state(OnboardingStates.shops)
    
    data = await state.get_data()
    selected = data.get("selected_shops", [])
    
    shops_text = (
        "📋 <b>Шаг 2 из 4: Магазины</b>\n\n"
        "Выбери магазины и маркетплейсы, где обычно совершаешь покупки.\n\n"
        "Мы будем показывать тебе предложения именно из этих магазинов.\n\n"
        f"Выбрано: {len(selected)}"
    )
    
    keyboard = get_shops_keyboard(selected)
    await callback.message.edit_text(shops_text, reply_markup=keyboard)


@router.callback_query(F.data == "onb:next_from_price")
async def callback_next_to_notifications(callback: CallbackQuery, state: FSMContext):
    """Переход к шагу 4: уведомления."""
    await callback.answer()
    
    data = await state.get_data()
    selected_prices = data.get("selected_price_ranges", [])
    
    if not selected_prices:
        await callback.answer(
            "⚠️ Выбери хотя бы один ценовой диапазон!",
            show_alert=True
        )
        return
    
    await state.set_state(OnboardingStates.notifications)
    
    notif_text = (
        "📋 <b>Шаг 4 из 4: Уведомления</b>\n\n"
        "Как часто ты хочешь получать уведомления о новых предложениях?\n\n"
        "Выбери один вариант:"
    )
    
    keyboard = get_notifications_keyboard()
    await callback.message.edit_text(notif_text, reply_markup=keyboard)


def get_notifications_keyboard() -> InlineKeyboardBuilder:
    """Создает клавиатуру для выбора частоты уведомлений."""
    builder = InlineKeyboardBuilder()
    
    for name, freq_id in NOTIFICATION_FREQ:
        builder.button(
            text=name,
            callback_data=f"onb_notif:{freq_id}"
        )
    
    builder.adjust(1)
    
    # Навигация
    builder.row(
        InlineKeyboardBuilder().button(
            text="⬅️ Назад",
            callback_data="onb:back_to_price"
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(F.data.startswith("onb_notif:"))
async def callback_select_notification_freq(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора частоты уведомлений."""
    await callback.answer()
    
    freq_id = callback.data.split(":")[1]
    await state.update_data(notification_frequency=freq_id)
    
    # Если выбран режим дайджеста - спрашиваем время
    if freq_id in ["daily", "twice_daily"]:
        await state.set_state(OnboardingStates.notification_time)
        
        time_text = (
            "🕐 <b>Выбор времени уведомлений</b>\n\n"
            "В какое время тебе удобно получать уведомления?\n\n"
            "Выбери предпочитаемое время:"
        )
        
        keyboard = get_notification_time_keyboard()
        await callback.message.edit_text(time_text, reply_markup=keyboard)
    else:
        # Если не нужно время - сразу показываем итоги
        await show_summary(callback.message, state)


def get_notification_time_keyboard() -> InlineKeyboardBuilder:
    """Создает клавиатуру для выбора времени уведомлений."""
    builder = InlineKeyboardBuilder()
    
    for name, time_id in NOTIFICATION_TIMES:
        builder.button(
            text=name,
            callback_data=f"onb_time:{time_id}"
        )
    
    builder.adjust(2)
    
    # Навигация
    builder.row(
        InlineKeyboardBuilder().button(
            text="⬅️ Назад",
            callback_data="onb:back_to_notifications"
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(F.data.startswith("onb_time:"))
async def callback_select_notification_time(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора времени уведомлений."""
    await callback.answer()
    
    time_id = callback.data.split(":")[1]
    await state.update_data(notification_time=time_id)
    
    # Показываем итоговую сводку
    await show_summary(callback.message, state)


@router.callback_query(F.data == "onb:back_to_price")
async def callback_back_to_price(callback: CallbackQuery, state: FSMContext):
    """Возврат к шагу 3: ценовой диапазон."""
    await callback.answer()
    await state.set_state(OnboardingStates.price_range)
    
    data = await state.get_data()
    selected = data.get("selected_price_ranges", [])
    
    price_text = (
        "📋 <b>Шаг 3 из 4: Ценовой диапазон</b>\n\n"
        "Укажи в каком ценовом диапазоне ты обычно ищешь товары.\n\n"
        "Можешь выбрать несколько вариантов или 'Любой'.\n\n"
        f"Выбрано: {len(selected)}"
    )
    
    keyboard = get_price_keyboard(selected)
    await callback.message.edit_text(price_text, reply_markup=keyboard)


@router.callback_query(F.data == "onb:back_to_notifications")
async def callback_back_to_notifications(callback: CallbackQuery, state: FSMContext):
    """Возврат к шагу 4: уведомления."""
    await callback.answer()
    await state.set_state(OnboardingStates.notifications)
    
    notif_text = (
        "📋 <b>Шаг 4 из 4: Уведомления</b>\n\n"
        "Как часто ты хочешь получать уведомления о новых предложениях?\n\n"
        "Выбери один вариант:"
    )
    
    keyboard = get_notifications_keyboard()
    await callback.message.edit_text(notif_text, reply_markup=keyboard)


async def show_summary(message: Message, state: FSMContext):
    """
    Показывает итоговую сводку выбранных настроек перед сохранением.
    
    Args:
        message: Объект сообщения
        state: FSM контекст с собранными данными
    """
    await state.set_state(OnboardingStates.summary)
    data = await state.get_data()
    
    # Форматируем категории
    selected_cats = data.get("selected_categories", [])
    cat_names = [name for name, cat_id in CATEGORIES if cat_id in selected_cats]
    categories_str = ", ".join(cat_names) if cat_names else "Не выбрано"
    
    # Форматируем магазины
    selected_shops = data.get("selected_shops", [])
    shop_names = [name for name, shop_id in SHOPS if shop_id in selected_shops]
    shops_str = ", ".join(shop_names) if shop_names else "Не выбрано"
    
    # Форматируем цены
    selected_prices = data.get("selected_price_ranges", [])
    price_names = [name for name, price_id in PRICE_RANGES if price_id in selected_prices]
    prices_str = ", ".join(price_names) if price_names else "Не выбрано"
    
    # Форматируем уведомления
    notif_freq = data.get("notification_frequency", "")
    freq_name = next((name for name, freq_id in NOTIFICATION_FREQ if freq_id == notif_freq), "Не выбрано")
    
    notif_time = data.get("notification_time", "")
    time_str = ""
    if notif_time:
        time_name = next((name for name, time_id in NOTIFICATION_TIMES if time_id == notif_time), "")
        time_str = f"\n  Время: {time_name}"
    
    summary_text = (
        "✅ <b>Проверь свои настройки</b>\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>Категории:</b>\n{categories_str}\n\n"
        f"🏪 <b>Магазины:</b>\n{shops_str}\n\n"
        f"💰 <b>Ценовой диапазон:</b>\n{prices_str}\n\n"
        f"🔔 <b>Уведомления:</b>\n{freq_name}{time_str}\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "Всё верно? Сохраняем настройки?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💾 Сохранить", callback_data="onb:save")
    builder.button(text="🔄 Начать заново", callback_data="onboarding:restart")
    builder.button(text="⬅️ Назад", callback_data="onb:back_to_notifications")
    builder.adjust(1)
    
    await message.edit_text(summary_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "onb:save")
async def callback_save_preferences(callback: CallbackQuery, state: FSMContext):
    """
    Сохранение настроек в базу данных.
    
    Создает или обновляет запись в таблице UserPreference.
    """
    await callback.answer()
    user_id = callback.from_user.id
    
    data = await state.get_data()
    
    async with async_session_maker() as session:
        try:
            # Проверяем есть ли уже настройки
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            prefs = result.scalar_one_or_none()
            
            # Парсим price ranges для извлечения min/max
            selected_prices = data.get("selected_price_ranges", [])
            price_min = None
            price_max = None
            
            if "any" not in selected_prices:
                # Извлекаем минимум и максимум из выбранных диапазонов
                all_mins = []
                all_maxs = []
                
                for price_range in selected_prices:
                    if price_range == "10000+":
                        all_mins.append(10000)
                        all_maxs.append(999999)
                    else:
                        parts = price_range.split("-")
                        all_mins.append(int(parts[0]))
                        all_maxs.append(int(parts[1]))
                
                if all_mins and all_maxs:
                    price_min = min(all_mins)
                    price_max = max(all_maxs)
            
            # Парсим время уведомлений
            notif_time = data.get("notification_time")
            time_obj = None
            if notif_time:
                hour, minute = map(int, notif_time.split(":"))
                time_obj = dt_time(hour, minute)
            
            if prefs:
                # Обновляем существующие настройки
                prefs.categories = data.get("selected_categories", [])
                prefs.favorite_shops = data.get("selected_shops", [])
                prefs.price_range_min = price_min
                prefs.price_range_max = price_max
                prefs.notification_frequency = data.get("notification_frequency", "instant")
                prefs.notification_time = time_obj
            else:
                # Создаем новые настройки
                prefs = UserPreference(
                    user_id=user_id,
                    categories=data.get("selected_categories", []),
                    favorite_shops=data.get("selected_shops", []),
                    price_range_min=price_min,
                    price_range_max=price_max,
                    notification_frequency=data.get("notification_frequency", "instant"),
                    notification_time=time_obj
                )
                session.add(prefs)
            
            await session.commit()
            
            await state.clear()
            
            success_text = (
                "🎉 <b>Отлично! Настройки сохранены</b>\n\n"
                "Теперь бот будет показывать тебе только релевантные предложения!\n\n"
                "Ты можешь изменить настройки в любой момент:\n"
                "• Через команду /setup\n"
                "• Через раздел ⚙️ Настройки в главном меню\n\n"
                "Используй /start чтобы вернуться в главное меню."
            )
            
            await callback.message.edit_text(success_text)
            
            logger.info(f"Пользователь {user_id} успешно настроил персонализацию")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек пользователя {user_id}: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ Произошла ошибка при сохранении настроек.\n\n"
                "Попробуй еще раз через /setup"
            )
            await state.clear()