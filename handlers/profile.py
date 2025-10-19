from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from database.connection import async_session_maker
from database.models import User, Subscription
from config.settings import settings

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """
    Обработчик команды /profile - показывает информацию о профиле пользователя.
    
    Эта функция загружает из базы данных:
    - Основную информацию пользователя (имя, дата регистрации)
    - Статус подписки (активна/истекла, тип, дата окончания)
    - Реферальный код для приглашения друзей
    - Статистику (будет расширена на следующих этапах)
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    
    # Открываем асинхронную сессию для работы с базой данных
    async with async_session_maker() as session:
        try:
            # Загружаем данные пользователя из таблицы users
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Если пользователь не найден в базе (не должно происходить)
                await message.answer(
                    "Произошла ошибка. Попробуй команду /start для регистрации."
                )
                logger.warning(f"Пользователь {user_id} не найден в базе при запросе профиля")
                return
            
            # Загружаем активную подписку пользователя
            subscription_result = await session.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .order_by(Subscription.end_date.desc())
            )
            subscription = subscription_result.scalar_one_or_none()
            
            # Формируем текст профиля с информацией о пользователе
            profile_text = f"👤 <b>Твой профиль</b>\n\n"
            profile_text += f"<b>Имя:</b> {user.first_name}"
            
            # Добавляем фамилию если она есть
            if user.last_name:
                profile_text += f" {user.last_name}"
            
            profile_text += "\n"
            
            # Показываем username если он установлен в Telegram
            if user.username:
                profile_text += f"<b>Username:</b> @{user.username}\n"
            
            # Форматируем дату регистрации в читаемый формат
            reg_date = user.registration_date.strftime("%d.%m.%Y")
            profile_text += f"<b>Дата регистрации:</b> {reg_date}\n\n"
            
            # Информация о подписке
            profile_text += "⭐ <b>Подписка:</b>\n"
            
            if subscription:
                # Проверяем активна ли подписка на текущий момент
                is_active = subscription.end_date > datetime.now()
                
                # Определяем иконку и текст статуса
                status_icon = "✅" if is_active else "❌"
                status_text = "Активна" if is_active else "Истекла"
                
                # Форматируем тип подписки для отображения
                sub_type_display = {
                    'trial': 'Пробная',
                    'paid': 'Оплаченная',
                    'expired': 'Истекшая'
                }.get(subscription.subscription_type, subscription.subscription_type)
                
                profile_text += f"{status_icon} <b>Статус:</b> {status_text}\n"
                profile_text += f"<b>Тип:</b> {sub_type_display}\n"
                
                # Показываем дату окончания
                end_date = subscription.end_date.strftime("%d.%m.%Y %H:%M")
                profile_text += f"<b>Действует до:</b> {end_date}\n"
                
                # Если подписка скоро истекает - предупреждаем пользователя
                days_left = (subscription.end_date - datetime.now()).days
                if is_active and days_left <= 3:
                    profile_text += f"\n⚠️ Осталось {days_left} дней до окончания подписки!\n"
            else:
                # Если подписки нет совсем (не должно происходить)
                profile_text += "❌ Подписка не активна\n"
            
            profile_text += "\n"
            
            # Реферальная информация
            profile_text += "👥 <b>Реферальная программа:</b>\n"
            profile_text += f"<b>Твой код:</b> <code>{user.referral_code}</code>\n"
            
            # Формируем реферальную ссылку (замените your_bot на имя вашего бота)
            bot_username = (await message.bot.get_me()).username
            referral_link = f"https://t.me/{bot_username}?start=ref_{user.referral_code}"
            profile_text += f"<b>Ссылка для друзей:</b>\n<code>{referral_link}</code>\n\n"
            
            # Статистика (будет расширена на следующих этапах)
            profile_text += "📊 <b>Статистика:</b>\n"
            profile_text += "• Приглашено друзей: 0 (скоро)\n"
            profile_text += "• Сэкономлено всего: 0 ₽ (скоро)\n"
            profile_text += "• Отслеживаемых товаров: 0 (скоро)\n"
            
            # Создаем клавиатуру с кнопками действий
            keyboard = InlineKeyboardBuilder()
            
            keyboard.row(
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="profile:settings"
                )
            )
            
            keyboard.row(
                InlineKeyboardButton(
                    text="⭐ Управление подпиской",
                    callback_data="menu:subscription"
                )
            )
            
            keyboard.row(
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="profile:back_to_menu"
                )
            )
            
            await message.answer(
                text=profile_text,
                reply_markup=keyboard.as_markup()
            )
            
            logger.info(f"Профиль показан пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке профиля пользователя {user_id}: {e}", exc_info=True)
            await message.answer(
                "Произошла ошибка при загрузке профиля. Попробуй позже."
            )


@router.callback_query(F.data == "profile:settings")
async def callback_profile_settings(callback: CallbackQuery):
    """
    Обработчик кнопки "Настройки" из профиля.
    
    Показывает настройки персонализации и уведомлений.
    Эта функция будет расширена на следующих этапах с реальными настройками.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    await callback.answer()
    
    settings_text = (
        "⚙️ <b>Настройки</b>\n\n"
        "Этот раздел будет реализован на следующих этапах.\n\n"
        "Доступные настройки:\n"
        "• Категории интересов\n"
        "• Любимые магазины\n"
        "• Ценовой диапазон\n"
        "• Частота уведомлений\n"
        "• Время получения уведомлений\n"
        "• Язык интерфейса\n\n"
        "Используй /profile чтобы вернуться в профиль."
    )
    
    # Кнопка возврата в профиль
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="👤 Вернуться в профиль",
            callback_data="profile:back"
        )
    )
    
    await callback.message.edit_text(
        text=settings_text,
        reply_markup=keyboard.as_markup()
    )
    
    logger.info(f"Пользователь {callback.from_user.id} открыл настройки профиля")


@router.callback_query(F.data == "menu:subscription")
async def callback_subscription_management(callback: CallbackQuery):
    """
    Обработчик кнопки "Управление подпиской".
    
    Показывает информацию о текущей подписке и варианты оплаты.
    Интеграция платежей будет реализована на следующих этапах.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    await callback.answer()
    
    subscription_text = (
        "⭐ <b>Управление подпиской</b>\n\n"
        "Этот раздел находится в разработке.\n\n"
        "Здесь ты сможешь:\n"
        "• Продлить подписку\n"
        "• Изменить тариф\n"
        "• Настроить автопродление\n"
        "• Посмотреть историю платежей\n"
        "• Получить чек\n\n"
        "Интеграция платежных систем будет добавлена на следующих этапах.\n\n"
        "Используй /profile чтобы вернуться в профиль."
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="👤 Вернуться в профиль",
            callback_data="profile:back"
        )
    )
    
    await callback.message.edit_text(
        text=subscription_text,
        reply_markup=keyboard.as_markup()
    )
    
    logger.info(f"Пользователь {callback.from_user.id} открыл управление подпиской")


@router.callback_query(F.data == "profile:back")
async def callback_back_to_profile(callback: CallbackQuery):
    """
    Обработчик кнопки возврата в профиль.
    
    Эмулирует команду /profile для повторного отображения профиля.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    await callback.answer()
    
    # Создаем псевдо-сообщение для повторного использования логики cmd_profile
    # В реальности просто вызываем ту же функцию загрузки профиля
    await cmd_profile(callback.message)
    
    logger.info(f"Пользователь {callback.from_user.id} вернулся в профиль")


@router.callback_query(F.data == "profile:back_to_menu")
async def callback_back_to_main_menu(callback: CallbackQuery):
    """
    Обработчик кнопки "Главное меню" из профиля.
    
    Возвращает пользователя в главное меню бота.
    
    Args:
        callback: Callback query от нажатия на кнопку
    """
    await callback.answer()
    
    # Импортируем функцию показа главного меню
    from handlers.menu import show_main_menu, get_main_menu_keyboard
    
    menu_text = (
        "🏠 <b>Главное меню</b>\n\n"
        "Выбери нужный раздел из меню ниже:"
    )
    
    await callback.message.edit_text(
        text=menu_text,
        reply_markup=get_main_menu_keyboard()
    )
    
    logger.info(f"Пользователь {callback.from_user.id} вернулся в главное меню из профиля")