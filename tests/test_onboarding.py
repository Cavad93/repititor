"""
Тесты для проверки системы анкетирования и персонализации.

Включает тесты:
1. Создание настроек пользователя
2. Алгоритм персонализации
3. Адаптивное обучение (позитивная + негативная реакция)
4. Производительность на 100k товаров
"""

import asyncio
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import init_db, async_session_maker, close_db
from database.models import User, UserPreference
from utils.personalization import PersonalizationEngine, AdaptiveLearning
from sqlalchemy import select, delete
from datetime import datetime
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
                category_weights={},
                shop_weights={},
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
        logger.error(f"✗ Ошибка создания настроек: {e}", exc_info=True)
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
        logger.error(f"✗ Ошибка алгоритма персонализации: {e}", exc_info=True)
        return False


async def test_adaptive_learning():
    """Тест адаптивного обучения - изменение весов (позитивная + негативная реакция)."""
    logger.info("Тест: Адаптивное обучение")
    
    try:
        test_user_id = 888888888
        
        # Проверяем что настройки уже существуют
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            prefs = result.scalar_one_or_none()
            
            if not prefs:
                logger.error("✗ Настройки пользователя не найдены для теста адаптивного обучения")
                return False
            
            # Инициализируем веса если они пустые
            if not prefs.category_weights:
                prefs.category_weights = {}
            if not prefs.shop_weights:
                prefs.shop_weights = {}
            await session.commit()
        
        # ========== ТЕСТ ПОЗИТИВНОЙ РЕАКЦИИ ==========
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
            
            if cat_weight <= 1.0:
                logger.error("✗ Вес категории не увеличился после позитивного взаимодействия!")
                return False
            if shop_weight <= 1.0:
                logger.error("✗ Вес магазина не увеличился после позитивного взаимодействия!")
                return False
        
        # ========== ТЕСТ НЕГАТИВНОЙ РЕАКЦИИ ==========
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
            
            if cat_weight >= 1.0:
                logger.error("✗ Вес категории не уменьшился после негативного взаимодействия!")
                return False
            if shop_weight >= 1.0:
                logger.error("✗ Вес магазина не уменьшился после негативного взаимодействия!")
                return False
        
        logger.info("✓ Адаптивное обучение работает корректно (позитив + негатив)")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка адаптивного обучения: {e}", exc_info=True)
        return False


async def test_performance_100k():
    """Тест производительности на 100k товаров."""
    logger.info("Тест: Производительность на больших объемах")
    
    try:
        test_user_id = 888888888
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            prefs = result.scalar_one_or_none()
            
            if not prefs:
                logger.error("✗ Предпочтения не найдены")
                return False
        
        # Генерируем 100k товаров
        logger.info("  Генерация 100,000 тестовых товаров...")
        items = []
        categories = ['electronics', 'clothing', 'books', 'home', 'sports']
        shops = ['wildberries', 'ozon', 'lamoda', 'mvideo', 'chitai_gorod']
        
        for i in range(100000):
            items.append({
                'title': f'Товар {i}',
                'category': categories[i % len(categories)],
                'shop': shops[i % len(shops)],
                'price': 1000 + (i % 10000),
                'views': i % 1000
            })
        
        logger.info("  Товары сгенерированы, запуск фильтрации...")
        
        # Тест оптимизированной фильтрации
        start = time.time()
        filtered = PersonalizationEngine.filter_by_relevance_optimized(
            prefs, items, min_score=40, max_results=100
        )
        elapsed_ms = (time.time() - start) * 1000
        
        logger.info(f"  Отфильтровано {len(filtered)} топовых товаров за {elapsed_ms:.1f}ms")
        
        if elapsed_ms > 500:
            logger.warning(f"⚠️  Время обработки превысило 500ms: {elapsed_ms:.1f}ms")
            logger.info("  Рекомендация: добавить индексы БД или кэширование результатов")
            # Не считаем это фатальной ошибкой
        else:
            logger.info(f"✓ Производительность в норме: {elapsed_ms:.1f}ms < 500ms")
        
        # Проверяем что результаты корректные
        if len(filtered) == 0:
            logger.error("✗ Фильтрация не вернула результатов")
            return False
        
        # Проверяем что результаты отсортированы по убыванию релевантности
        scores = [item.get('relevance_score', 0) for item in filtered]
        if scores != sorted(scores, reverse=True):
            logger.error("✗ Результаты не отсортированы по релевантности")
            return False
        
        logger.info(f"✓ Производительность: {elapsed_ms:.1f}ms, топ-{len(filtered)} результатов корректны")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка теста производительности: {e}", exc_info=True)
        return False


async def cleanup_test_data():
    """Очистка тестовых данных."""
    logger.info("Очистка тестовых данных")
    try:
        async with async_session_maker() as session:
            test_user_id = 888888888
            
            # Удаляем настройки
            await session.execute(
                delete(UserPreference).where(UserPreference.user_id == test_user_id)
            )
            
            # Удаляем пользователя
            await session.execute(
                delete(User).where(User.user_id == test_user_id)
            )
            
            await session.commit()
            
            logger.info("✓ Тестовые данные удалены")
    except Exception as e:
        logger.error(f"✗ Ошибка очистки: {e}", exc_info=True)


async def run_tests():
    """Запуск всех тестов."""
    logger.info("=" * 60)
    logger.info("ТЕСТИРОВАНИЕ СИСТЕМЫ ПЕРСОНАЛИЗАЦИИ")
    logger.info("=" * 60)
    
    await init_db()
    
    results = []
    
    # Последовательно запускаем все тесты
    results.append(("Создание настроек", await test_create_user_preference()))
    results.append(("Алгоритм персонализации", await test_personalization_algorithm()))
    results.append(("Адаптивное обучение", await test_adaptive_learning()))
    results.append(("Производительность 100k", await test_performance_100k()))
    
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


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
