"""
Миграции базы данных для обновления схемы.
"""

import logging
from sqlalchemy import text
from database.connection import engine

logger = logging.getLogger(__name__)


async def migrate_add_adaptive_weights():
    """
    Миграция: Добавляет поля category_weights и shop_weights в user_preferences.
    
    Для SQLite используем ALTER TABLE ADD COLUMN.
    Поля инициализируются пустыми JSON объектами {}.
    """
    logger.info("Запуск миграции: добавление адаптивных весов")
    
    async with engine.begin() as conn:
        try:
            # Проверяем существует ли уже колонка category_weights
            result = await conn.execute(
                text("PRAGMA table_info(user_preferences)")
            )
            columns = [row[1] for row in result]
            
            if 'category_weights' not in columns:
                # Добавляем category_weights
                await conn.execute(
                    text("""
                        ALTER TABLE user_preferences 
                        ADD COLUMN category_weights TEXT DEFAULT '{}'
                    """)
                )
                logger.info("✓ Колонка category_weights добавлена")
            else:
                logger.info("✓ Колонка category_weights уже существует")
            
            if 'shop_weights' not in columns:
                # Добавляем shop_weights
                await conn.execute(
                    text("""
                        ALTER TABLE user_preferences 
                        ADD COLUMN shop_weights TEXT DEFAULT '{}'
                    """)
                )
                logger.info("✓ Колонка shop_weights добавлена")
            else:
                logger.info("✓ Колонка shop_weights уже существует")
            
            logger.info("Миграция завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении миграции: {e}", exc_info=True)
            raise


async def run_all_migrations():
    """
    Запускает все доступные миграции.
    Вызывается при старте приложения.
    """
    logger.info("=" * 60)
    logger.info("ЗАПУСК МИГРАЦИЙ БАЗЫ ДАННЫХ")
    logger.info("=" * 60)
    
    await migrate_add_adaptive_weights()
    await migrate_add_affiliate_tables()  # НОВОЕ
    
    logger.info("=" * 60)
    logger.info("ВСЕ МИГРАЦИИ ЗАВЕРШЕНЫ")
    logger.info("=" * 60)


async def migrate_add_affiliate_tables():
    """
    Миграция: Создает таблицы для партнерских программ и кэшбэка.
    
    Добавляет:
    - affiliate_links
    - cashback_transactions
    - user_balances
    - balance_operations
    """
    logger.info("Запуск миграции: создание таблиц партнерских программ")
    
    from database.models import AffiliateLink, CashbackTransaction, UserBalance, BalanceOperation
    from database.connection import Base, engine
    
    async with engine.begin() as conn:
        try:
            # Создаем все новые таблицы
            await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✓ Таблицы партнерских программ созданы")
            logger.info("  - affiliate_links")
            logger.info("  - cashback_transactions")
            logger.info("  - user_balances")
            logger.info("  - balance_operations")
            
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)
            raise
