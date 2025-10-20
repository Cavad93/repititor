# handlers/promotions.py

"""
Обработчики для просмотра акций и скидок.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker
from services.promotions.storage import PromotionStorage
from services.cashback.cashback_service import CashbackService

logger = logging.getLogger(__name__)
router = Router()

cashback_service = CashbackService()


@router.message(Command("deals"))
async def cmd_deals(message: Message):
    """
    Команда /deals - показывает актуальные акции.
    """
    try:
        async with async_session_maker() as session:
            # Получаем топ акций
            promotions = await PromotionStorage.get_top_promotions(
                limit=10,
                category=None
            )
            
            if not promotions:
                await message.answer(
                    "🔍 Актуальных акций пока нет.\n"
                    "Попробуйте позже!"
                )
                return
            
            # Показываем акции
            text = "🔥 <b>Топ актуальных акций:</b>\n\n"
            
            for i, promo in enumerate(promotions, 1):
                text += f"{i}. <b>{promo['title']}</b>\n"
                text += f"   🏪 {promo['shop']}\n"
                
                if promo.get('discount_percent'):
                    text += f"   💰 Скидка: {promo['discount_percent']}%\n"
                
                if promo.get('price_new'):
                    price_rub = promo['price_new'] / 100
                    text += f"   💵 Цена: {price_rub:.2f} ₽\n"
                
                text += "\n"
            
            # Кнопки
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Показать еще",
                    callback_data="deals:more"
                )],
                [InlineKeyboardButton(
                    text="Фильтры",
                    callback_data="deals:filters"
                )]
            ])
            
            await message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Ошибка в cmd_deals: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("promo:"))
async def callback_promo_detail(callback: CallbackQuery):
    """
    Показывает детали акции.
    """
    try:
        await callback.answer()
        
        # Извлекаем ID акции
        promo_id = int(callback.data.split(":")[1])
        
        # Получаем акцию
        async with async_session_maker() as session:
            promo = await PromotionStorage.get_by_id(promo_id)
            
            if not promo:
                await callback.message.edit_text("Акция не найдена")
                return
            
            # Формируем сообщение
            text = f"<b>{promo['title']}</b>\n\n"
            text += f"🏪 <b>Магазин:</b> {promo['shop']}\n"
            text += f"📂 <b>Категория:</b> {promo['category']}\n\n"
            
            if promo.get('description'):
                text += f"📝 {promo['description']}\n\n"
            
            if promo.get('discount_percent'):
                text += f"💰 <b>Скидка:</b> {promo['discount_percent']}%\n"
            
            if promo.get('price_new'):
                price_rub = promo['price_new'] / 100
                text += f"💵 <b>Цена:</b> {price_rub:.2f} ₽\n"
                
                if promo.get('price_old'):
                    old_price_rub = promo['price_old'] / 100
                    text += f"~~{old_price_rub:.2f} ₽~~\n"
            
            if promo.get('promo_code'):
                text += f"\n🎟 <b>Промокод:</b> <code>{promo['promo_code']}</code>\n"
            
            # Генерируем кэшбэк-ссылку
            cashback_link = await cashback_service.get_cashback_link(
                shop=promo['shop'],
                original_url=promo.get('url'),
                user_id=callback.from_user.id
            )
            
            # Кнопки
            buttons = []
            
            if cashback_link:
                buttons.append([InlineKeyboardButton(
                    text=f"🎁 Купить с кэшбэком {cashback_link['cashback_percent']}",
                    url=cashback_link['url']
                )])
                text += f"\n💸 <b>Кэшбэк:</b> {cashback_link['cashback_percent']}"
            elif promo.get('url'):
                buttons.append([InlineKeyboardButton(
                    text="🔗 Перейти к акции",
                    url=promo['url']
                )])
            
            buttons.append([InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="deals:back"
            )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            # Отправляем (с картинкой если есть)
            if promo.get('image_url'):
                await callback.message.answer_photo(
                    photo=promo['image_url'],
                    caption=text,
                    reply_markup=keyboard
                )
                await callback.message.delete()
            else:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=keyboard
                )
    
    except Exception as e:
        logger.error(f"Ошибка в callback_promo_detail: {e}", exc_info=True)
        await callback.answer("Ошибка загрузки акции", show_alert=True)