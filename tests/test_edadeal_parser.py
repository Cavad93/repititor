# tests/test_edadeal_parser.py

"""
Тест парсинга Едадила.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.promotions.edadeal_parser import EdadealParser
from services.promotions.storage import PromotionStorage
from database.connection import init_db, close_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_parse():
    """Тестирование парсинга."""
    logger.info("Инициализация БД...")
    await init_db()
    
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ ПАРСИНГА ЕДАДИЛА")
    logger.info("="*60)
    
    parser = EdadealParser()
    
    # Парсим акции
    promotions = await parser.parse(
        city='moskva',
        categories=['food'],
        max_pages=1
    )
    
    logger.info(f"\n✓ Получено {len(promotions)} акций")
    
    # Показываем примеры
    if promotions:
        logger.info("\nПримеры акций:")
        for promo in promotions[:3]:
            logger.info(f"\n  Название: {promo['title']}")
            logger.info(f"  Магазин: {promo['shop']}")
            logger.info(f"  Категория: {promo['category']}")
            logger.info(f"  Скидка: {promo.get('discount_percent', 0)}%")
    
    # Сохраняем в БД
    logger.info("\nСохранение в БД...")
    saved = await PromotionStorage.save_promotions(promotions)
    logger.info(f"✓ Сохранено: {saved}")
    
    await close_db()


if __name__ == "__main__":
    asyncio.run(test_parse())