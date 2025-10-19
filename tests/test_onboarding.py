"""
Тесты для проверки системы анкетирования и персонализации.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import init_db, async_session_maker, close_db
from database.models import User, UserPreference
from utils.personalization import PersonalizationEngine
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_create_user_preference():
    """Тест создания настроек пользователя."""
    logger.info("Тест: Создание настроек персонализации")
    
    try:
        async with async_session_maker() as session:
            test_user_id = 888888888
            
            # Создаем тестового пользователя если его нет
            result = await session.execute(
                select(User).where(User.user_id == test_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                from datetime import datetime
                user = User(
                    user_id=test_user_id,
                    username="test_onboarding",
                    first_name="Тест",
                    registration_date=datetime.now(),
                    last_activity=datetime.now()
                )
                session.add(user)
                await session.commit()
            
            # Создаем настройки
            prefs = UserPreference(
                user_id=test_user_id,
                categories=["electronics", "clothing"],
                favorite_shops=["wildberries", "ozon"],
                price_range_min=1000,
                price_range_max=10000,
                notification_frequency="daily"
            )
            
            session.add(prefs)
            await session.commit()
            
            logger.info("✓ Настройки созданы успешно")
            logger.info(f"  Категории: {prefs.categories}")
            logger.info(f"  Магазины: {prefs.favorite_shops}")
            logger.info(f"  Цены: {prefs.price_range_min} - {prefs.price_range_max}")
            
            return True
    except Exception as e:
        logger.error(f"✗ Ошибка создания настроек: {e}")
        return False


async def test_personalization_algorithm():
    """Тест алгоритма персонализации."""
    logger.info("Тест: Алгоритм персонализации")
    
    try:
        async with async_session_maker() as session:
            test_user_id = 888888888
            
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            prefs = result.scalar_one_or_none()
            
            if not prefs:
                logger.error("✗ Настройки пользователя не найдены")
                return False
            
            # Тестовые предложения
            test_items = [
                {
                    'title': 'Смартфон Samsung',
                    'category': 'electronics',
                    'shop': 'wildberries',
                    'price': 5000,
                    'views': 100
                },
                {
                    'title': 'Куртка зимняя',
                    'category': 'clothing',
                    'shop': 'ozon',
                    'price': 3000,
                    'views': 50
                },
                {
                    'title': 'Книга по программированию',
                    'category': 'books',
                    'shop': 'chitai_gorod',
                    'price': 500,
                    'views': 20
                }
            ]
            
            logger.info("Оценка релевантности товаров:")
            for item in test_items:
                score = PersonalizationEngine.calculate_relevance_score(
                    prefs, item, item['views']
                )
                relevance = PersonalizationEngine.categorize_by_relevance(score)
                logger.info(f"  {item['title']}: {score} баллов ({relevance})")
            
            # Тест фильтрации
            filtered = PersonalizationEngine.filter_by_relevance(prefs, test_items)
            logger.info(f"\n✓ Отфильтровано {len(filtered)} релевантных товара из {len(test_items)}")
            
            return True
    except Exception as e:
        logger.error(f"✗ Ошибка алгоритма персонализации: {e}")
        return False

async def test_adaptive_learning():
    """Тест адаптивного обучения - изменение весов."""
    logger.info("Тест: Адаптивное обучение")
    
    from utils.personalization import AdaptiveLearning
    
    try:
        test_user_id = 888888888
        
        # Создаем пользователя и настройки если их нет
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.user_id == test_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                from datetime import datetime
                user = User(
                    user_id=test_user_id,
                    username="test_adaptive",
                    first_name="Тест",
                    registration_date=datetime.now(),
                    last_activity=datetime.now()
                )
                session.add(user)
                await session.commit()
            
            # Создаем настройки если их нет
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            prefs = result.scalar_one_or_none()
            
            if not prefs:
                prefs = UserPreference(
                    user_id=test_user_id,
                    categories=["electronics", "clothing"],
                    favorite_shops=["wildberries", "ozon"],
                    price_range_min=1000,
                    price_range_max=10000,
                    notification_frequency="daily",
                    category_weights={},
                    shop_weights={}
                )
                session.add(prefs)
                await session.commit()
        
        # Симулируем ПОЗИТИВНОЕ взаимодействие
        logger.info("  Тестируем позитивное взаимодействие (click)...")
        await AdaptiveLearning.process_interaction(
            user_id=test_user_id,
            action_type='click',
            item_category='electronics',
            item_shop='wildberries'
        )
        
        # Проверяем что веса ВЫРОСЛИ
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            prefs = result.scalar_one_or_none()
            
            cat_weight = prefs.category_weights.get('electronics', 1.0)
            shop_weight = prefs.shop_weights.get('wildberries', 1.0)
            
            logger.info(f"  После click: категория 'electronics' = {cat_weight:.2f}")
            logger.info(f"  После click: магазин 'wildberries' = {shop_weight:.2f}")
            
            if cat_weight <= 1.0 or shop_weight <= 1.0:
                logger.error("✗ Веса не увеличились после позитивного взаимодействия!")
                return False
        
        # Симулируем НЕГАТИВНОЕ взаимодействие
        logger.info("  Тестируем негативное взаимодействие (hide)...")
        await AdaptiveLearning.process_interaction(
            user_id=test_user_id,
            action_type='hide',
            item_category='clothing',
            item_shop='ozon'
        )
        
        # Проверяем что веса УМЕНЬШИЛИСЬ
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            prefs = result.scalar_one_or_none()
            
            cat_weight = prefs.category_weights.get('clothing', 1.0)
            shop_weight = prefs.shop_weights.get('ozon', 1.0)
            
            logger.info(f"  После hide: категория 'clothing' = {cat_weight:.2f}")
            logger.info(f"  После hide: магазин 'ozon' = {shop_weight:.2f}")
            
            if cat_weight >= 1.0 or shop_weight >= 1.0:
                logger.error("✗ Веса не уменьшились после негативного взаимодействия!")
                return False
        
        logger.info("✓ Адаптивное обучение работает корректно")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка адаптивного обучения: {e}", exc_info=True)
        return False


async def cleanup_test_data():
    """Очистка тестовых данных."""
    logger.info("Очистка тестовых данных")
    try:
        from sqlalchemy import delete
        
        async with async_session_maker() as session:
            test_user_id = 888888888
            
            await session.execute(
                delete(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            await session.execute(
                delete(User).where(User.user_id == test_user_id)
            )
            await session.commit()
            
            logger.info("✓ Тестовые данные удалены")
    except Exception as e:
        logger.error(f"✗ Ошибка очистки: {e}")


async def run_tests():
    """Запуск всех тестов."""
    logger.info("=" * 60)
    logger.info("ТЕСТИРОВАНИЕ СИСТЕМЫ ПЕРСОНАЛИЗАЦИИ")
    logger.info("=" * 60)
    
    await init_db()
    
    results = []
    results.append(("Создание настроек", await test_create_user_preference()))
    results.append(("Алгоритм персонализации", await test_personalization_algorithm()))
    results.append(("Адаптивное обучение", await test_adaptive_learning()))
    
    await cleanup_test_data()
    await close_db()
    
    logger.info("=" * 60)
    logger.info("РЕЗУЛЬТАТЫ")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    logger.info(f"\nПройдено: {passed}/{len(results)}")
    logger.info("=" * 60)
    
    return passed == len(results)

async def test_adaptive_learning():
    """Тест адаптивного обучения."""
    logger.info("Тест: Адаптивное обучение")
    
    from utils.personalization import AdaptiveLearning
    
    test_user_id = 888888888
    
    # Симулируем позитивное взаимодействие
    await AdaptiveLearning.process_interaction(
        user_id=test_user_id,
        action_type='click',
        item_category='electronics',
        item_shop='wildberries'
    )
    
    # Проверяем что веса изменились
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == test_user_id)
        )
        prefs = result.scalar_one_or_none()
        
        assert prefs.category_weights.get('electronics', 1.0) > 1.0, "Вес категории должен вырасти"
        logger.info(f"✓ Вес категории 'electronics': {prefs.category_weights.get('electronics')}")
    
    return True
    
if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
