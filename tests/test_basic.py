"""
Базовые тесты для проверки работоспособности основных компонентов бота.

Эти тесты проверяют критические функции без необходимости запуска бота:
- Инициализацию базы данных
- Создание и чтение записей пользователей
- Генерацию реферальных кодов
- Работу с подписками
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import init_db, async_session_maker, close_db
from database.models import User, Subscription, generate_referral_code
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_init():
    """Тест инициализации базы данных."""
    logger.info("Тест 1: Инициализация базы данных")
    try:
        await init_db()
        logger.info("✓ База данных успешно инициализирована")
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка инициализации БД: {e}")
        return False


async def test_create_user():
    """Тест создания нового пользователя."""
    logger.info("Тест 2: Создание пользователя")
    try:
        async with async_session_maker() as session:
            test_user_id = 999999999
            
            new_user = User(
                user_id=test_user_id,
                username="test_user",
                first_name="Тест",
                last_name="Тестов",
                registration_date=datetime.now(),
                last_activity=datetime.now(),
                is_active=True
            )
            
            session.add(new_user)
            await session.commit()
            
            logger.info(f"✓ Пользователь создан с ID: {test_user_id}")
            logger.info(f"  Реферальный код: {new_user.referral_code}")
            return True
    except Exception as e:
        logger.error(f"✗ Ошибка создания пользователя: {e}")
        return False


async def test_create_subscription():
    """Тест создания подписки для пользователя."""
    logger.info("Тест 3: Создание подписки")
    try:
        async with async_session_maker() as session:
            test_user_id = 999999999
            
            trial_end = datetime.now() + timedelta(days=settings.TRIAL_DAYS)
            subscription = Subscription(
                user_id=test_user_id,
                subscription_type='trial',
                start_date=datetime.now(),
                end_date=trial_end,
                is_trial_used=True,
                auto_renewal=False
            )
            
            session.add(subscription)
            await session.commit()
            
            logger.info(f"✓ Подписка создана до {trial_end.strftime('%Y-%m-%d')}")
            logger.info(f"  Активна: {subscription.is_active}")
            return True
    except Exception as e:
        logger.error(f"✗ Ошибка создания подписки: {e}")
        return False


async def test_read_user():
    """Тест чтения данных пользователя из БД."""
    logger.info("Тест 4: Чтение данных пользователя")
    try:
        from sqlalchemy import select
        
        async with async_session_maker() as session:
            test_user_id = 999999999
            
            result = await session.execute(
                select(User).where(User.user_id == test_user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                logger.info(f"✓ Пользователь найден: {user.first_name} {user.last_name}")
                logger.info(f"  Username: @{user.username}")
                logger.info(f"  Реферальный код: {user.referral_code}")
                return True
            else:
                logger.error("✗ Пользователь не найден")
                return False
    except Exception as e:
        logger.error(f"✗ Ошибка чтения пользователя: {e}")
        return False


async def test_referral_code_unique():
    """Тест уникальности реферальных кодов."""
    logger.info("Тест 5: Уникальность реферальных кодов")
    try:
        codes = set()
        for _ in range(1000):
            code = generate_referral_code()
            codes.add(code)
        
        if len(codes) == 1000:
            logger.info("✓ Все 1000 сгенерированных кодов уникальны")
            logger.info(f"  Примеры кодов: {list(codes)[:5]}")
            return True
        else:
            logger.error(f"✗ Обнаружены дубликаты: {1000 - len(codes)} повторов")
            return False
    except Exception as e:
        logger.error(f"✗ Ошибка генерации кодов: {e}")
        return False


async def cleanup_test_data():
    """Очистка тестовых данных после выполнения тестов."""
    logger.info("Очистка тестовых данных")
    try:
        from sqlalchemy import delete
        
        async with async_session_maker() as session:
            test_user_id = 999999999
            
            await session.execute(
                delete(Subscription).where(Subscription.user_id == test_user_id)
            )
            await session.execute(
                delete(User).where(User.user_id == test_user_id)
            )
            await session.commit()
            
            logger.info("✓ Тестовые данные удалены")
    except Exception as e:
        logger.error(f"✗ Ошибка очистки данных: {e}")


async def run_all_tests():
    """Запуск всех тестов последовательно."""
    logger.info("=" * 60)
    logger.info("ЗАПУСК БАЗОВЫХ ТЕСТОВ REPITITOR БОТА")
    logger.info("=" * 60)
    
    results = []
    
    results.append(("Инициализация БД", await test_database_init()))
    results.append(("Создание пользователя", await test_create_user()))
    results.append(("Создание подписки", await test_create_subscription()))
    results.append(("Чтение пользователя", await test_read_user()))
    results.append(("Уникальность кодов", await test_referral_code_unique()))
    
    await cleanup_test_data()
    await close_db()
    
    logger.info("=" * 60)
    logger.info("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("=" * 60)
    logger.info(f"Пройдено тестов: {passed}/{total}")
    logger.info("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)