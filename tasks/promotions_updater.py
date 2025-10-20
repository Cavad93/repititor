# tasks/promotions_updater.py

"""
Фоновая задача для периодического обновления акций.
"""

import logging
import asyncio
from datetime import datetime

from services.promotions.edadeal_parser import EdadealParser
from services.promotions.storage import PromotionStorage

logger = logging.getLogger(__name__)


async def update_promotions_task():
    """
    Обновляет акции из Едадила.
    
    Вызывается периодически (например, каждые 6 часов).
    """
    logger.info("=" * 60)
    logger.info(f"ЗАПУСК ОБНОВЛЕНИЯ АКЦИЙ: {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        # Инициализируем парсер
        parser = EdadealParser()
        
        # Парсим акции для основных городов
        cities = ['moskva', 'sankt-peterburg']
        
        all_promotions = []
        
        for city in cities:
            logger.info(f"\n--- Город: {city} ---")
            
            # Парсим все категории
            promotions = await parser.parse(
                city=city,
                categories=['food', 'pharmacy', 'beauty', 'children'],
                max_pages=3  # 3 страницы * 30 акций = ~90 акций на категорию
            )
            
            all_promotions.extend(promotions)
            
            logger.info(f"Получено {len(promotions)} акций для {city}")
        
        # Сохраняем в БД
        logger.info(f"\nСохранение {len(all_promotions)} акций в БД...")
        saved_count = await PromotionStorage.save_promotions(all_promotions)
        
        # Деактивируем истекшие
        await PromotionStorage.deactivate_expired()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✓ ОБНОВЛЕНИЕ ЗАВЕРШЕНО: {saved_count} акций")
        logger.info("=" * 60)
        
        return saved_count
    
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА обновления акций: {e}", exc_info=True)
        return 0


async def run_periodic_updater(interval_hours: int = 6):
    """
    Запускает периодическое обновление акций.
    
    Args:
        interval_hours: Интервал обновления в часах
    """
    logger.info(f"Запуск периодического обновления акций (каждые {interval_hours}ч)")
    
    while True:
        try:
            await update_promotions_task()
        except Exception as e:
            logger.error(f"Ошибка в цикле обновления: {e}")
        
        # Ждем до следующего обновления
        await asyncio.sleep(interval_hours * 3600)