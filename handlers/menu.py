from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)

router = Router()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню бота.
    
    Меню структурировано по рядам для удобной навигации:
    - Первый ряд: основные функции поиска и отслеживания
    - Второй ряд: финансовые функции (кэшбэк, история)
    - Третий ряд: настройки и подписка
    - Четвертый ряд: помощь и реферальная программа
    
    Каждая кнопка отправляет callback с уникальным идентификатором,
    который затем обрабатывается соответствующим handler'ом.
    
    Returns:
        InlineKeyboardMarkup: Готовая клавиатура для отправки пользователю
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Найти скидки",
            callback_data="menu:find_deals"
        ),
        InlineKeyboardButton(
            text="👀 Мои товары",
            callback_data="menu:tracked_items"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="💳 Промокоды и кэшбэк",
            callback_data="menu:cashback"
        ),
        InlineKeyboardButton(
            text="📊 История экономии",
            callback_data="menu:savings_history"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="menu:settings"
        ),
        InlineKeyboardButton(
            text="⭐ Подписка",
            callback_data="menu:subscription"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="menu:help"
        ),
        InlineKeyboardButton(
            text="👥 Пригласить друга",
            callback_data="menu:referral"
        )
    )
    
    return builder.as_markup()


async def show_main_menu(message: Message):
    """
    Отображает главное меню пользователю.
    
    Эта функция используется после регистрации, при возврате в меню
    или когда пользователь хочет увидеть доступные опции.
    
    Args:
        message: Объект сообщения для ответа пользователю
    """
    try:
        menu_text = (
            "🏠 <b>Главное меню</b>\n\n"
            "Выбери нужный раздел из меню ниже:"
        )
        
        await message.answer(
            text=menu_text,
            reply_markup=get_main_menu_keyboard()
        )
        
        logger.info(f"Главное меню показано пользователю {message.from_user.id}")
    
    except Exception as e:
        logger.error(f"Ошибка при отображении главного меню для пользователя {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке меню. Попробуй команду /start еще раз.")


@router.callback_query(F.data == "menu:find_deals")
async def callback_find_deals(callback: CallbackQuery):
    """
    Обработчик кнопки "Найти скидки".
    
    Эта функция будет расширена на следующих этапах с реальным поиском
    скидок и акций в популярных магазинах.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "🔍 <b>Поиск скидок</b>\n\n"
            "Этот раздел находится в разработке и будет доступен на следующих этапах.\n\n"
            "Здесь ты сможешь:\n"
            "• Искать актуальные скидки по категориям\n"
            "• Фильтровать по магазинам и ценам\n"
            "• Получать персонализированные рекомендации\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл раздел поиска скидок")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике поиска скидок для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)


@router.callback_query(F.data == "menu:tracked_items")
async def callback_tracked_items(callback: CallbackQuery):
    """
    Обработчик кнопки "Мои товары" - отслеживаемые товары пользователя.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "👀 <b>Мои отслеживаемые товары</b>\n\n"
            "Этот раздел будет реализован на следующих этапах.\n\n"
            "Функции раздела:\n"
            "• Список отслеживаемых товаров\n"
            "• Текущие цены и история изменений\n"
            "• Уведомления о снижении цен\n"
            "• Быстрое добавление новых товаров\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл отслеживаемые товары")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике отслеживаемых товаров для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)


@router.callback_query(F.data == "menu:cashback")
async def callback_cashback(callback: CallbackQuery):
    """
    Обработчик кнопки "Промокоды и кэшбэк".
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "💳 <b>Промокоды и кэшбэк</b>\n\n"
            "Раздел в разработке. Скоро здесь появятся:\n\n"
            "• Актуальные промокоды для популярных магазинов\n"
            "• Интеграция с кэшбэк-сервисами\n"
            "• Автоматический поиск лучших предложений\n"
            "• История использованных промокодов\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл промокоды и кэшбэк")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике промокодов для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)


@router.callback_query(F.data == "menu:savings_history")
async def callback_savings_history(callback: CallbackQuery):
    """
    Обработчик кнопки "История экономии".
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "📊 <b>История экономии</b>\n\n"
            "Этот раздел будет доступен после реализации основного функционала.\n\n"
            "Здесь ты увидишь:\n"
            "• Общую сумму сэкономленных средств\n"
            "• Статистику по месяцам и категориям\n"
            "• Самые выгодные покупки\n"
            "• Графики и аналитику\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл историю экономии")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике истории экономии для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)


@router.callback_query(F.data == "menu:settings")
async def callback_settings(callback: CallbackQuery):
    """
    Обработчик кнопки "Настройки".
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            "Этот раздел будет реализован на следующих этапах.\n\n"
            "Доступные настройки:\n"
            "• Категории интересов\n"
            "• Любимые магазины\n"
            "• Ценовой диапазон\n"
            "• Частота уведомлений\n"
            "• Время получения уведомлений\n"
            "• Язык интерфейса\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл настройки")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике настроек для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)


@router.callback_query(F.data == "menu:help")
async def callback_help(callback: CallbackQuery):
    """
    Обработчик кнопки "Помощь" - дублирует команду /help.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        help_text = (
            "❓ <b>Помощь и поддержка</b>\n\n"
            "Используй команду /help для подробной справки по всем функциям бота.\n\n"
            "Если у тебя возникли вопросы или проблемы:\n"
            "• Проверь раздел FAQ (в разработке)\n"
            "• Напиши в поддержку (функция скоро появится)\n"
            "• Посети наш канал с новостями (будет добавлен)\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        await callback.message.edit_text(help_text)
        logger.info(f"Пользователь {callback.from_user.id} открыл помощь")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике помощи для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)


@router.callback_query(F.data == "menu:referral")
async def callback_referral(callback: CallbackQuery):
    """
    Обработчик кнопки "Пригласить друга" - реферальная программа.
    
    Показывает пользователю его реферальный код и ссылку для приглашения друзей.
    Эта функция будет расширена с отображением статистики приглашенных.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "👥 <b>Реферальная программа</b>\n\n"
            "Приглашай друзей и получай бонусы!\n\n"
            "Твоя реферальная ссылка:\n"
            "<code>t.me/your_bot?start=ref_CODE</code>\n\n"
            "За каждого приглашенного друга ты получишь:\n"
            "🎁 +7 дней подписки\n"
            "💰 Бонусы в будущем\n\n"
            "Полная статистика будет доступна на следующих этапах.\n\n"
            "Нажми /start чтобы вернуться в главное меню."
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл реферальную программу")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике реферальной программы для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуй позже.", show_alert=True)
