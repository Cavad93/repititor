# database/migrations/004_add_promotions.py

"""
Миграция: добавление таблицы promotions для хранения акций.
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def upgrade(session):
    """Создание таблицы promotions."""
    logger.info("Создание таблицы promotions...")
    
    # Создаем таблицу напрямую через SQL
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS promotions (
            promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id VARCHAR(255) NOT NULL,
            source VARCHAR(50) NOT NULL DEFAULT 'edadeal',
            title VARCHAR(512) NOT NULL,
            description VARCHAR(2048),
            shop VARCHAR(100) NOT NULL,
            category VARCHAR(100) NOT NULL,
            price_old INTEGER,
            price_new INTEGER,
            discount_percent INTEGER,
            discount_amount INTEGER,
            promo_code VARCHAR(100),
            url VARCHAR(2048),
            image_url VARCHAR(2048),
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            views_count INTEGER DEFAULT 0 NOT NULL,
            clicks_count INTEGER DEFAULT 0 NOT NULL,
            quality_score INTEGER DEFAULT 50 NOT NULL,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            extra_data TEXT
        )
    """))
    
    # Создаем индексы
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_promotions_external_id 
        ON promotions(external_id)
    """))
    
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_promotions_shop 
        ON promotions(shop)
    """))
    
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_promotions_category 
        ON promotions(category)
    """))
    
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_promotions_end_date 
        ON promotions(end_date)
    """))
    
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_promotions_is_active 
        ON promotions(is_active)
    """))
    
    await session.commit()
    logger.info("✓ Таблица promotions успешно создана")


async def downgrade(session):
    """Удаление таблицы promotions."""
    logger.info("Удаление таблицы promotions...")
    await session.execute(text("DROP TABLE IF EXISTS promotions"))
    await session.commit()
    logger.info("✓ Таблица promotions удалена")