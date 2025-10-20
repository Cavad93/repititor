# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config.settings import settings
from database.connection import init_db
from handlers import registration, menu, profile, onboarding, cashback, deals
from utils.logger import setup_logging


async def main():
    """
    Главная функция для запуска бота.
    Инициализирует все необходимые компоненты и запускает polling.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Запуск бота...")
    
    # Инициализация БД и применение миграций
    await init_db()
    logger.info("База данных инициализирована")
    
    try:
        from database.migrations import run_all_migrations
        await run_all_migrations()
    except Exception as e:
        logger.warning(f"Ошибка при запуске миграций (возможно, уже применены): {e}")
    
    # Создание экземпляра бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Dispatcher для обработки сообщений
    dp = Dispatcher()
    
    # Подключение всех роутеров
    dp.include_router(registration.router)
    dp.include_router(menu.router)
    dp.include_router(profile.router)
    dp.include_router(onboarding.router)
    dp.include_router(cashback.router)
    dp.include_router(deals.router)  # НОВОЕ: Роутер акций и скидок
    
    # Подключение админ-команд (опционально)
    try:
        from utils import admin_commands
        dp.include_router(admin_commands.router)
        logger.info("Админ-команды подключены")
    except ImportError:
        logger.info("Модуль admin_commands не найден, пропускаем")
    
    logger.info("Обработчики подключены")
    
    # Запуск фоновых задач
    from tasks.cashback_checker import run_periodic_checker
    from tasks.promotions_updater import run_periodic_updater
    
    asyncio.create_task(run_periodic_checker(interval_hours=1))
    asyncio.create_task(run_periodic_updater(interval_hours=6))
    logger.info("Фоновые задачи запущены (проверка кэшбэка + обновление акций)")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот успешно запущен и готов к работе")
        
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nФатальная ошибка: {e}")
