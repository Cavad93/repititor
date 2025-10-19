import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config.settings import settings
from database.connection import init_db
from handlers import registration, menu, profile, onboarding, cashback
from utils.logger import setup_logging


async def main():
    """
    Главная функция для запуска бота.
    Инициализирует все необходимые компоненты и запускает polling.
    """
    # Настраиваем логирование для отслеживания работы бота
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Запуск бота...")
    
    # Инициализируем подключение к базе данных
    # Это создаст все необходимые таблицы если их еще нет
    await init_db()
    logger.info("База данных инициализирована")
    
    # Запускаем миграции для обновления схемы БД
    try:
        from database.migrations import run_all_migrations
        await run_all_migrations()
    except Exception as e:
        logger.warning(f"Ошибка при запуске миграций (возможно, уже применены): {e}")
    
    # Создаем экземпляр бота с токеном из настроек
    # ParseMode.HTML позволяет использовать HTML-разметку в сообщениях
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Dispatcher управляет обработкой входящих сообщений и callback'ов
    dp = Dispatcher()
    
    # Подключаем роутеры из разных модулей-обработчиков
    # Это модульный подход - каждый раздел функционала в отдельном файле
    dp.include_router(registration.router)
    dp.include_router(menu.router)
    dp.include_router(profile.router)
    dp.include_router(onboarding.router)
    dp.include_router(cashback.router)  # НОВОЕ: Роутер кэшбэка
    
    logger.info("Обработчики подключены")
    
    # Запускаем фоновую задачу проверки заказов
    from tasks.cashback_checker import run_periodic_checker
    asyncio.create_task(run_periodic_checker(interval_hours=1))
    logger.info("Фоновая задача проверки заказов запущена")
    
    try:
        # Удаляем все pending updates при старте
        # Это гарантирует что бот обработает только новые сообщения
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот успешно запущен и готов к работе")
        
        # Запускаем polling - бот начинает принимать сообщения
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        # Корректное закрытие соединений при остановке бота
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    # Запускаем асинхронную main функцию
    # asyncio.run() управляет event loop автоматически
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nФатальная ошибка: {e}")
