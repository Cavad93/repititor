from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging
from aiogram.fsm.context import FSMContext

from database.connection import async_session_maker
from database.models import User, Subscription
from config.settings import settings
from handlers.menu import show_main_menu

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start - первая точка входа в бота.
    
    Этот handler выполняет несколько важных задач:
    1. Извлекает реферальный код из параметров команды если он есть
    2. Проверяет существует ли пользователь в базе данных
    3. Если пользователь новый - создает запись и назначает пробную подписку
    4. Если пользователь существующий - обновляет время последней активности
    5. Показывает приветственное сообщение и главное меню
    
    Формат команды с реферальным кодом: /start ref_ABC12345
    Реферальный код идет после префикса "ref_"
    
    Args:
        message: Объект сообщения от Telegram с информацией о пользователе
        state: FSM контекст для управления состояниями анкетирования
    """
    # Получаем Telegram ID пользователя - это уникальный идентификатор
    user_id = message.from_user.id
    
    # Извлекаем реферальный код из глубокой ссылки если он есть
    # Команда может быть /start или /start ref_CODE123
    referral_code = None
    if message.text and len(message.text.split()) > 1:
        # Разбиваем текст команды на части
        args = message.text.split()[1]
        # Проверяем что аргумент начинается с префикса ref_
        if args.startswith('ref_'):
            # Извлекаем сам код без префикса
            referral_code = args[4:]
            logger.info(f"Пользователь {user_id} пришел по реферальной ссылке: {referral_code}")
    
    # Открываем асинхронную сессию для работы с базой данных
    async with async_session_maker() as session:
        try:
            # Пытаемся найти пользователя в базе по его Telegram ID
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Пользователь уже зарегистрирован - просто обновляем активность
                existing_user.last_activity = datetime.now()
                await session.commit()
                
                logger.info(f"Существующий пользователь {user_id} (@{message.from_user.username}) вернулся в бота")
                
                # Приветствуем вернувшегося пользователя
                await message.answer(
                    f"С возвращением, {message.from_user.first_name}! 👋\n\n"
                    "Рад снова видеть тебя. Давай найдем для тебя лучшие скидки!"
                )
                
                # Показываем главное меню существующему пользователю
                await show_main_menu(message)
                
            else:
                # Это новый пользователь - создаем запись в базе
                logger.info(f"Регистрация нового пользователя {user_id} (@{message.from_user.username})")
                
                # Если указан реферальный код - проверяем существует ли пригласивший
                referrer_id = None
                if referral_code:
                    # Ищем пользователя с таким реферальным кодом
                    referrer_result = await session.execute(
                        select(User).where(User.referral_code == referral_code)
                    )
                    referrer = referrer_result.scalar_one_or_none()
                    if referrer:
                        referrer_id = referrer.user_id
                        logger.info(f"Найден реферер: {referrer_id} для нового пользователя {user_id}")
                    else:
                        logger.warning(f"Реферальный код {referral_code} не найден")
                
                # Создаем нового пользователя с данными из Telegram
                # Валидация и санитизация данных пользователя
                username = message.from_user.username[:255] if message.from_user.username else None
                first_name = message.from_user.first_name[:255] if message.from_user.first_name else "Пользователь"
                last_name = message.from_user.last_name[:255] if message.from_user.last_name else None

                new_user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    registration_date=datetime.now(),
                    last_activity=datetime.now(),
                    is_active=True,
                    referred_by=referrer_id
                )
                session.add(new_user)
                
                # Создаем пробную подписку на указанный период
                # Дата окончания = текущая дата + количество дней из настроек
                trial_end = datetime.now() + timedelta(days=settings.TRIAL_DAYS)
                trial_subscription = Subscription(
                    user_id=user_id,
                    subscription_type='trial',
                    start_date=datetime.now(),
                    end_date=trial_end,
                    is_trial_used=True,
                    auto_renewal=False
                )
                session.add(trial_subscription)
                
                # Сохраняем все изменения в базе данных атомарно
                await session.commit()
                
                logger.info(f"Пользователь {user_id} успешно зарегистрирован с пробной подпиской до {trial_end}")
                
                # Отправляем приветственное сообщение новому пользователю
                welcome_text = (
                    f"Привет, {message.from_user.first_name}! 👋\n\n"
                    f"Добро пожаловать в <b>Repititor</b> - твоего личного помощника в поиске скидок и экономии! 💰\n\n"
                    f"🎁 <b>Ты получил {settings.TRIAL_DAYS} дней бесплатного доступа!</b>\n\n"
                    f"Что я умею:\n"
                    f"🔍 Находить лучшие скидки и акции\n"
                    f"💳 Показывать актуальные промокоды и кэшбэк\n"
                    f"📊 Отслеживать цены на интересующие товары\n"
                    f"📱 Уведомлять о новых выгодных предложениях\n\n"
                    f"Твой уникальный реферальный код: <code>{new_user.referral_code}</code>\n"
                    f"Приглашай друзей и получай бонусы! 🎉"
                )
                
                if referrer_id:
                    # Если пользователь пришел по реферальной ссылке - благодарим за это
                    welcome_text += "\n\n✨ Спасибо что пришел по приглашению друга!"
                
                await message.answer(welcome_text)
                
                # Предлагаем пройти анкетирование для персонализации
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                
                onboarding_builder = InlineKeyboardBuilder()
                onboarding_builder.button(
                    text="🎯 Настроить персонализацию",
                    callback_data="registration:start_onboarding"
                )
                onboarding_builder.button(
                    text="⏭️ Пропустить (настрою позже)",
                    callback_data="registration:skip_onboarding"
                )
                onboarding_builder.adjust(1)
                
                await message.answer(
                    "🎯 <b>Персонализация рекомендаций</b>\n\n"
                    "Хочешь настроить бота под свои интересы прямо сейчас?\n\n"
                    "Это займет 2-3 минуты, и ты будешь получать только релевантные предложения!\n\n"
                    "Или можешь сделать это позже через команду /setup",
                    reply_markup=onboarding_builder.as_markup()
                )
            
        except Exception as e:
            # Логируем любые ошибки в процессе регистрации
            logger.error(f"Ошибка при обработке команды /start для пользователя {user_id}: {e}", exc_info=True)
            # Откатываем изменения если что-то пошло не так
            await session.rollback()
            # Информируем пользователя о проблеме
            await message.answer(
                "Произошла ошибка при регистрации. Пожалуйста, попробуй еще раз или обратись в поддержку."
            )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help - показывает справку по возможностям бота.
    
    Это подробное руководство помогает пользователю понять все функции
    и научиться пользоваться ботом эффективно.
    
    Args:
        message: Объект сообщения от пользователя
    """
    help_text = (
        "📖 <b>Справка по использованию бота</b>\n\n"
        
        "<b>🔍 Поиск скидок</b>\n"
        "Находи актуальные скидки и распродажи в популярных магазинах. "
        "Бот автоматически фильтрует предложения по твоим интересам.\n\n"
        
        "<b>👀 Отслеживание товаров</b>\n"
        "Добавь товары в список отслеживаемых и получай уведомления "
        "когда цена снизится или появится скидка.\n\n"
        
        "<b>💳 Промокоды и кэшбэк</b>\n"
        "Получай актуальные промокоды для популярных магазинов "
        "и узнавай о предложениях кэшбэк-сервисов.\n\n"
        
        "<b>📊 История экономии</b>\n"
        "Смотри сколько ты сэкономил благодаря боту и какие покупки "
        "были самыми выгодными.\n\n"
        
        "<b>⚙️ Настройки персонализации</b>\n"
        "Настрой категории товаров, любимые магазины и частоту уведомлений "
        "для персонального опыта.\n\n"
        
        "<b>👥 Реферальная программа</b>\n"
        "Приглашай друзей и получай бонусные дни подписки за каждого "
        "приглашенного пользователя.\n\n"
        
        "<b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/profile - Твой профиль\n\n"
        
        "❓ Остались вопросы? Пиши в поддержку через раздел 'Помощь' в меню."
    )
    
    await message.answer(help_text)
    logger.info(f"Пользователь {message.from_user.id} запросил справку")

@router.callback_query(F.data == "registration:start_onboarding")
async def callback_start_onboarding_after_registration(callback: CallbackQuery, state: FSMContext):
    """Запуск анкетирования сразу после регистрации."""
    from handlers.onboarding import start_onboarding
    
    await callback.answer()
    await start_onboarding(callback.message, state, is_restart=False)


@router.callback_query(F.data == "registration:skip_onboarding")
async def callback_skip_onboarding(callback: CallbackQuery):
    """Пропуск анкетирования."""
    await callback.answer()
    await callback.message.edit_text(
        "Хорошо! Ты можешь настроить персонализацию в любой момент:\n"
        "• Команда /setup\n"
        "• Раздел ⚙️ Настройки в главном меню\n\n"
        "Используй /start для открытия главного меню."
    )
    
    logger.info(f"Пользователь {callback.from_user.id} пропустил анкетирование")
