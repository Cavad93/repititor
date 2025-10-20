# handlers/deals.py

"""
Обработчик раздела "Найти скидки" с персонализацией.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.connection import async_session_maker
from database.models import UserPreference, Promotion, UserInteraction
from services.promotions.storage import PromotionStorage
from utils.personalization import PersonalizationEngine
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "menu:find_deals")
async def callback_find_deals(callback: CallbackQuery):
    """
    Главный обработчик "Найти скидки".
    
    Показывает персонализированные акции на основе предпочтений пользователя.
    """
    await callback.answer()
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        # Загружаем предпочтения пользователя
        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            # Пользователь не прошел анкетирование
            await callback.message.edit_text(
                "🔍 <b>Найти скидки</b>\n\n"
                "Чтобы получать персонализированные акции, "
                "пройди анкетирование командой /setup\n\n"
                "Пока покажу популярные акции:"
            )
            
            # Показываем общие акции без персонализации
            promotions = await PromotionStorage.get_active_promotions(limit=10)
        else:
            # Получаем акции по предпочтениям пользователя
            promotions = await get_personalized_promotions(prefs)
        
        if not promotions:
            await callback.message.edit_text(
                "🔍 <b>Найти скидки</b>\n\n"
                "К сожалению, сейчас нет подходящих акций.\n"
                "Попробуй позже или измени настройки через /setup"
            )
            return
        
        # Показываем первую акцию
        await show_promotion_card(callback.message, promotions[0], prefs, 0, len(promotions))


async def get_personalized_promotions(prefs: UserPreference) -> list:
    """
    Получает персонализированные акции для пользователя.
    
    Args:
        prefs: Предпочтения пользователя
        
    Returns:
        List[Promotion]: Отсортированные по релевантности акции
    """
    # Получаем все активные акции
    all_promotions = await PromotionStorage.get_active_promotions(limit=200)
    
    # Конвертируем в формат для персонализации
    items = []
    for promo in all_promotions:
        items.append({
            'id': promo.promotion_id,
            'category': promo.category,
            'shop': promo.shop,
            'price': promo.price_new or 0,
            'discount_percent': promo.discount_percent or 0,
            'views': promo.views_count,
            'title': promo.title,
            'promo_object': promo  # Сохраняем объект
        })
    
    # Применяем персонализацию
    filtered = PersonalizationEngine.filter_and_rank(
        user_prefs=prefs,
        items=items,
        min_score=0.3,  # Порог релевантности
        max_results=20
    )
    
    # Возвращаем объекты Promotion
    return [item['promo_object'] for item in filtered]


async def show_promotion_card(message, promo: Promotion, prefs: UserPreference, index: int, total: int):
    """
    Показывает карточку одной акции.
    
    Args:
        message: Сообщение для редактирования
        promo: Акция для показа
        prefs: Предпочтения пользователя
        index: Текущий индекс (0-based)
        total: Общее количество акций
    """
    # Формируем текст
    text = f"🎁 <b>{promo.title}</b>\n\n"
    text += f"🏪 Магазин: {format_shop_name(promo.shop)}\n"
    
    if promo.price_old and promo.price_new:
        price_old_rub = promo.price_old / 100
        price_new_rub = promo.price_new / 100
        text += f"💰 Цена: <s>{price_old_rub:.2f}₽</s> → <b>{price_new_rub:.2f}₽</b>\n"
    
    if promo.discount_percent:
        text += f"📉 Скидка: <b>{promo.discount_percent}%</b>\n"
    
    if promo.promo_code:
        text += f"🎫 Промокод: <code>{promo.promo_code}</code>\n"
    
    if promo.end_date:
        text += f"⏰ До: {promo.end_date.strftime('%d.%m.%Y')}\n"
    
    if promo.description:
        desc = promo.description[:200] + "..." if len(promo.description) > 200 else promo.description
        text += f"\n{desc}\n"
    
    text += f"\n<i>Акция {index + 1} из {total}</i>"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    
    if promo.url:
        builder.button(text="🔗 Перейти к акции", url=promo.url)
    
    # Навигация
    nav_buttons = []
    if index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"deal:prev:{index}")
        )
    if index < total - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ Далее", callback_data=f"deal:next:{index}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Реакции
    builder.row(
        InlineKeyboardButton(text="👍 Интересно", callback_data=f"deal:like:{promo.promotion_id}"),
        InlineKeyboardButton(text="👎 Не интересно", callback_data=f"deal:dislike:{promo.promotion_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")
    )
    
    # Увеличиваем счетчик просмотров
    await PromotionStorage.increment_views(promo.promotion_id)
    
    try:
        await message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Ошибка показа акции: {e}")


@router.callback_query(F.data.startswith("deal:like:"))
async def callback_like_promotion(callback: CallbackQuery):
    """Обработчик положительной реакции на акцию."""
    await callback.answer("👍 Отлично! Учту твои предпочтения")
    
    promo_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    # Логируем взаимодействие
    await log_interaction(user_id, promo_id, "like")
    
    # Обновляем веса категорий/магазинов
    from utils.personalization import AdaptiveLearning
    await AdaptiveLearning.update_from_interaction(user_id, promo_id, positive=True)


@router.callback_query(F.data.startswith("deal:dislike:"))
async def callback_dislike_promotion(callback: CallbackQuery):
    """Обработчик негативной реакции на акцию."""
    await callback.answer("👎 Понял, буду показывать меньше таких")
    
    promo_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    # Логируем взаимодействие
    await log_interaction(user_id, promo_id, "dislike")
    
    # Обновляем веса
    from utils.personalization import AdaptiveLearning
    await AdaptiveLearning.update_from_interaction(user_id, promo_id, positive=False)


async def log_interaction(user_id: int, promo_id: int, action: str):
    """Логирует взаимодействие пользователя с акцией."""
    async with async_session_maker() as session:
        # Получаем данные акции
        result = await session.execute(
            select(Promotion).where(Promotion.promotion_id == promo_id)
        )
        promo = result.scalar_one_or_none()
        
        if not promo:
            return
        
        # Создаем запись взаимодействия
        interaction = UserInteraction(
            user_id=user_id,
            action_type=action,
            item_id=str(promo_id),
            item_category=promo.category,
            item_shop=promo.shop,
            item_price=promo.price_new
        )
        
        session.add(interaction)
        await session.commit()


def format_shop_name(shop: str) -> str:
    """Форматирует название магазина для показа."""
    names = {
        'pyaterochka': 'Пятёрочка',
        'magnit': 'Магнит',
        'perekrestok': 'Перекрёсток',
        'vkusvill': 'ВкусВилл',
        'lenta': 'Лента',
        'auchan': 'Ашан',
        'wildberries': 'Wildberries',
        'ozon': 'Ozon',
        'magnit_kosmetik': 'Магнит Косметик',
        'detskiy_mir': 'Детский Мир',
    }
    return names.get(shop, shop.title())


@router.callback_query(F.data == "back_to_main_menu")
async def callback_back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.answer()
    
    from handlers.menu import get_main_menu_keyboard
    
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выбери нужный раздел:",
        reply_markup=get_main_menu_keyboard()
    )