"""
Обработчики для работы с кэшбэком и партнерскими ссылками.

Позволяет пользователям получать кэшбэк-ссылки и отслеживать баланс.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc

from database.connection import async_session_maker
from database.models import UserBalance, AffiliateLink, CashbackTransaction
from services.affiliate.manager import AffiliateManager
from config.settings import settings
from utils.balance import BalanceManager

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """
    Команда /balance - показывает баланс кэшбэка пользователя.
    
    Отображает:
    - Текущий доступный баланс
    - Ожидающий подтверждения кэшбэк
    - Всего заработано
    - Историю операций
    """
    user_id = message.from_user.id
    
    async with async_session_maker() as session:
        try:
            # Получаем информацию о балансе
            balance_info = await BalanceManager.get_balance_info(session, user_id)
            
            balance_text = (
                "💰 <b>Ваш баланс кэшбэка</b>\n\n"
                f"💵 <b>Доступно:</b> {balance_info['current_balance']}₽\n"
                f"⏳ <b>Ожидает подтверждения:</b> {balance_info['pending_balance']}₽\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"• Всего заработано: {balance_info['total_earned']}₽\n"
                f"• Выведено: {balance_info['total_withdrawn']}₽\n\n"
            )
            
            # Минимальная сумма для вывода
            min_withdrawal = settings.MIN_WITHDRAWAL_AMOUNT
            
            if balance_info['current_balance'] >= min_withdrawal:
                balance_text += (
                    f"✅ Вы можете вывести средства!\n"
                    f"Минимальная сумма для вывода: {min_withdrawal}₽"
                )
            else:
                balance_text += (
                    f"⚠️ Минимальная сумма для вывода: {min_withdrawal}₽\n"
                    f"Осталось накопить: {min_withdrawal - balance_info['current_balance']}₽"
                )
            
            # Кнопки
            builder = InlineKeyboardBuilder()
            
            if balance_info['current_balance'] >= min_withdrawal:
                builder.button(text="💸 Вывести средства", callback_data="cashback:withdraw")
            
            builder.button(text="📜 История операций", callback_data="cashback:history")
            builder.button(text="❓ Как работает кэшбэк?", callback_data="cashback:help")
            builder.button(text="🏠 Главное меню", callback_data="profile:back_to_menu")
            builder.adjust(1)
            
            await message.answer(balance_text, reply_markup=builder.as_markup())
            
            logger.info(f"Пользователь {user_id} проверил баланс: {balance_info['current_balance']}₽")
            
        except Exception as e:
            logger.error(f"Ошибка при показе баланса для {user_id}: {e}", exc_info=True)
            await message.answer("Произошла ошибка при загрузке баланса. Попробуй позже.")


@router.callback_query(F.data == "cashback:history")
async def callback_cashback_history(callback: CallbackQuery):
    """
    Показывает историю транзакций кэшбэка.
    """
    await callback.answer()
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        try:
            # Загружаем последние 10 транзакций
            result = await session.execute(
                select(CashbackTransaction)
                .where(CashbackTransaction.user_id == user_id)
                .order_by(desc(CashbackTransaction.created_at))
                .limit(10)
            )
            transactions = result.scalars().all()
            
            if not transactions:
                await callback.message.edit_text(
                    "📜 <b>История кэшбэка</b>\n\n"
                    "У вас пока нет транзакций кэшбэка.\n\n"
                    "Используй кнопку 'Купить с кэшбэком' при просмотре товаров "
                    "чтобы получать кэшбэк с покупок!"
                )
                return
            
            history_text = "📜 <b>История кэшбэка</b>\n\n"
            history_text += "Последние 10 транзакций:\n\n"
            
            status_emoji = {
                'pending': '⏳',
                'confirmed': '✅',
                'paid': '💰',
                'rejected': '❌'
            }
            
            status_names = {
                'pending': 'Ожидает',
                'confirmed': 'Подтвержден',
                'paid': 'Выплачен',
                'rejected': 'Отклонен'
            }
            
            for tx in transactions:
                status = tx.status
                emoji = status_emoji.get(status, '❓')
                status_name = status_names.get(status, status)
                
                date_str = tx.created_at.strftime("%d.%m.%Y")
                
                history_text += (
                    f"{emoji} <b>{tx.cashback_amount}₽</b> — {status_name}\n"
                    f"   Дата: {date_str}\n"
                )
                
                if tx.order_amount:
                    history_text += f"   Заказ на: {tx.order_amount}₽\n"
                
                history_text += "\n"
            
            # Кнопка назад
            builder = InlineKeyboardBuilder()
            builder.button(text="⬅️ Назад к балансу", callback_data="cashback:back_to_balance")
            
            await callback.message.edit_text(history_text, reply_markup=builder.as_markup())
            
        except Exception as e:
            logger.error(f"Ошибка загрузки истории для {user_id}: {e}", exc_info=True)
            await callback.answer("Ошибка загрузки истории", show_alert=True)


@router.callback_query(F.data == "cashback:back_to_balance")
async def callback_back_to_balance(callback: CallbackQuery):
    """
    Возврат к просмотру баланса.
    """
    await callback.answer()
    # Эмулируем команду /balance
    await cmd_balance(callback.message)


@router.callback_query(F.data == "cashback:help")
async def callback_cashback_help(callback: CallbackQuery):
    """
    Помощь по работе с кэшбэком.
    """
    await callback.answer()
    
    help_text = (
        "❓ <b>Как работает кэшбэк?</b>\n\n"
        
        "<b>Шаг 1: Найди товар</b>\n"
        "Используй поиск скидок в боте или отправь ссылку на товар.\n\n"
        
        "<b>Шаг 2: Получи кэшбэк-ссылку</b>\n"
        "Нажми кнопку 'Купить с кэшбэком' — бот создаст специальную ссылку.\n\n"
        
        "<b>Шаг 3: Соверши покупку</b>\n"
        "Перейди по кэшбэк-ссылке и оформи заказ в магазине.\n\n"
        
        "<b>Шаг 4: Получи кэшбэк</b>\n"
        "После подтверждения заказа магазином (обычно 7-60 дней) "
        "кэшбэк будет начислен на твой баланс.\n\n"
        
        "💡 <b>Важно:</b>\n"
        "• Не используй блокировщики рекламы\n"
        "• Не очищай cookies перед покупкой\n"
        "• Оформляй заказ в течение 24 часов\n\n"
        
        f"💰 Минимальная сумма для вывода: {settings.MIN_WITHDRAWAL_AMOUNT}₽\n"
        f"⏰ Срок подтверждения: до {settings.CASHBACK_CONFIRMATION_DAYS} дней"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="cashback:back_to_balance")
    
    await callback.message.edit_text(help_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "cashback:withdraw")
async def callback_withdraw(callback: CallbackQuery):
    """
    Вывод средств (заглушка для будущей реализации).
    """
    await callback.answer()
    
    withdraw_text = (
        "💸 <b>Вывод средств</b>\n\n"
        "Функция вывода средств находится в разработке.\n\n"
        "Скоро будут доступны способы вывода:\n"
        "• На карту (СБП)\n"
        "• На телефон\n"
        "• На электронный кошелек\n\n"
        "Следи за обновлениями!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="cashback:back_to_balance")
    
    await callback.message.edit_text(withdraw_text, reply_markup=builder.as_markup())


@router.message(F.text.startswith('http'))
async def handle_product_url(message: Message):
    """
    Обработчик ссылок на товары.
    
    Когда пользователь отправляет ссылку на товар,
    бот автоматически создает кэшбэк-ссылку через Admitad.
    
    Процесс работы:
    1. Пользователь отправляет любую ссылку начинающуюся с http
    2. Бот определяет магазин по доменному имени
    3. Если магазин поддерживается, создается партнерская ссылка через Admitad
    4. Пользователь получает кэшбэк-ссылку для перехода на товар
    5. При покупке по этой ссылке ему начислится кэшбэк
    """
    user_id = message.from_user.id
    url = message.text.strip()
    
    await message.answer("🔄 Создаю кэшбэк-ссылку через Admitad, подожди немного...")
    
    try:
        # Инициализируем менеджер партнерских программ
        # Теперь передаем только настройки для Admitad
        affiliate_manager = AffiliateManager({
            'ADMITAD_AUTH_HEADER': settings.ADMITAD_AUTH_HEADER,
            'ADMITAD_WEBSITE_ID': settings.ADMITAD_WEBSITE_ID
        })
        
        # Генерируем партнерскую ссылку через Admitad
        result = await affiliate_manager.generate_affiliate_link(
            original_url=url,
            user_id=user_id,
            product_info=None
        )
        
        if result.get('error'):
            # Не удалось создать партнерскую ссылку
            await message.answer(
                f"⚠️ {result['error']}\n\n"
                "Вот оригинальная ссылка на товар:\n"
                f"{url}\n\n"
                "Ты можешь перейти по ней напрямую, но без кэшбэка."
            )
            return
        
        # Сохраняем ссылку в БД
        async with async_session_maker() as session:
            affiliate_link = AffiliateLink(
                user_id=user_id,
                original_url=url,
                affiliate_url=result['affiliate_url'],
                affiliate_network=result['network'],
                product_info={
                    'shop': result['shop']
                }
            )
            session.add(affiliate_link)
            await session.commit()
            
            # Добавляем pending баланс (примерный кэшбэк)
            # В реальности кэшбэк зависит от стоимости товара
            estimated_cashback = 100  # Примерная оценка
            await BalanceManager.add_pending_balance(session, user_id, estimated_cashback)
            await session.commit()
        
        # Отправляем результат
        cashback_percent = result['cashback_percent']
        network_name = result['network'].title()
        
        response_text = (
            f"✅ <b>Кэшбэк-ссылка готова!</b>\n\n"
            f"💰 Кэшбэк: до {cashback_percent}%\n"
            f"🏪 Магазин: {result['shop'].replace('_', ' ').title()}\n"
            f"🌐 Партнер: {network_name}\n\n"
            f"<b>Твоя ссылка с кэшбэком:</b>\n"
            f"{result['affiliate_url']}\n\n"
            f"⏰ Перейди по ссылке и соверши покупку в течение 24 часов.\n"
            f"После подтверждения заказа кэшбэк будет начислен на твой баланс."
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔗 Открыть ссылку", url=result['affiliate_url'])
        builder.button(text="💰 Мой баланс", callback_data="cashback:open_balance")
        builder.adjust(1)
        
        await message.answer(response_text, reply_markup=builder.as_markup())
        
        logger.info(
            f"Создана кэшбэк-ссылка для пользователя {user_id}: "
            f"{result['shop']} через {result['network']}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания кэшбэк-ссылки: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при создании кэшбэк-ссылки.\n\n"
            "Попробуй позже или используй прямую ссылку:\n"
            f"{url}"
        )


@router.callback_query(F.data == "cashback:open_balance")
async def callback_open_balance(callback: CallbackQuery):
    """
    Открывает баланс из inline кнопки.
    """
    await callback.answer()
    await cmd_balance(callback.message)
