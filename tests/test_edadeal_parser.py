# tests/test_edadeal_parser.py

"""
Полный тест парсинга Едадила с проверкой кэшбэка.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.promotions.edadeal_parser import EdadealParser
from services.promotions.storage import PromotionStorage
from services.cashback.cashback_service import CashbackService
from database.connection import init_db, close_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_parse():
    """
    Полный тест: парсинг + сохранение + кэшбэк.
    """
    logger.info("="*60)
    logger.info("ТЕСТ ПАРСИНГА ЕДАДИЛА")
    logger.info("="*60)
    
    # 1. Инициализация БД
    logger.info("\n1. Инициализация БД...")
    await init_db()
    logger.info("   ✓ БД готова")
    
    # 2. Парсинг акций
    logger.info("\n2. Парсинг акций...")
    parser = EdadealParser()
    
    promotions = await parser.parse(
        city='moskva',
        categories=['food', 'pharmacy'],
        max_pages=2
    )
    
    logger.info(f"   ✓ Получено {len(promotions)} акций")
    
    # 3. Примеры акций
    if promotions:
        logger.info("\n3. Примеры акций:")
        for i, promo in enumerate(promotions[:5], 1):
            logger.info(f"\n   [{i}] {promo['title']}")
            logger.info(f"       Магазин: {promo['shop']}")
            logger.info(f"       Категория: {promo['category']}")
            
            if promo.get('discount_percent'):
                logger.info(f"       Скидка: {promo['discount_percent']}%")
            
            if promo.get('price_new'):
                price = promo['price_new'] / 100
                logger.info(f"       Цена: {price:.2f} ₽")
            
            if promo.get('promo_code'):
                logger.info(f"       Промокод: {promo['promo_code']}")
    
    # 4. Сохранение в БД
    logger.info("\n4. Сохранение в БД...")
    saved = await PromotionStorage.save_promotions(promotions)
    logger.info(f"   ✓ Сохранено: {saved} акций")
    
    # 5. Проверка статистики
    logger.info("\n5. Статистика по магазинам:")
    stats = await PromotionStorage.get_stats_by_shop()
    for shop, count in stats.items():
        logger.info(f"   {shop}: {count} акций")
    
    # 6. Тест кэшбэка
    logger.info("\n6. Тест генерации кэшбэк-ссылок...")
    cashback_service = CashbackService()
    
    test_shops = ['пятерочка', 'aliexpress', 'ozon']
    for shop in test_shops:
        link = await cashback_service.get_cashback_link(
            shop=shop,
            user_id=12345
        )
        
        if link:
            logger.info(f"   {shop}: кэшбэк {link['cashback_percent']} ({link['network']})")
        else:
            logger.info(f"   {shop}: кэшбэк недоступен")
    
    # 7. Закрытие
    logger.info("\n7. Закрытие соединений...")
    await close_db()
    
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ ЗАВЕРШЕН УСПЕШНО")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(test_parse())
    except KeyboardInterrupt:
        logger.info("\nТест прерван пользователем")
    except Exception as e:
        logger.error(f"\nКРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
