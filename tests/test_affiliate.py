"""
Тесты для проверки партнерских программ.

Версия: Упрощенная - только Admitad
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from services.affiliate.admitad import AdmitadService
from services.affiliate.manager import AffiliateManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


async def test_admitad_connection():
    """
    Тест подключения к Admitad API.
    
    Проверяет:
    1. Наличие настроек в .env
    2. Корректность формата авторизационного заголовка
    3. Генерацию тестовой партнерской ссылки
    """
    logger.info("="*60)
    logger.info("ТЕСТ: Подключение к Admitad")
    logger.info("="*60)
    
    try:
        # Создаем сервис
        admitad = AdmitadService({
            'auth_header': settings.ADMITAD_AUTH_HEADER,
            'website_id': settings.ADMITAD_WEBSITE_ID
        })
        
        # Проверяем конфигурацию
        if not admitad.is_configured():
            logger.error("\n✗ Admitad не настроен")
            logger.info("\nЧто нужно сделать:")
            logger.info("1. Создайте файл .env в корне проекта")
            logger.info("2. Добавьте в него строки:")
            logger.info("   ADMITAD_AUTH_HEADER=Basic ваш_base64_токен")
            logger.info("   ADMITAD_WEBSITE_ID=ваш_website_id")
            return False
        
        logger.info("✓ Admitad настроен корректно")
        logger.info(f"  Website ID: {settings.ADMITAD_WEBSITE_ID}")
        auth_preview = settings.ADMITAD_AUTH_HEADER[:50] + "..." if len(settings.ADMITAD_AUTH_HEADER) > 50 else settings.ADMITAD_AUTH_HEADER
        logger.info(f"  Auth header: {auth_preview}")
        
        # Тестируем генерацию ссылки
        logger.info("\nГенерация тестовой deeplink...")
        logger.info("  Используем тестовый URL от Wildberries")
        
        test_url = "https://www.wildberries.ru/catalog/12345678/detail.aspx"
        test_user_id = 123456789
        
        logger.info(f"  Original URL: {test_url}")
        
        affiliate_link = await admitad.generate_affiliate_link(
            test_url, test_user_id
        )
        
        if affiliate_link:
            logger.info("\n✓ Deeplink создан успешно!")
            logger.info(f"  Партнерская ссылка: {affiliate_link[:100]}...")
            logger.info("\n  Что это означает:")
            logger.info("  • API Admitad работает корректно")
            logger.info("  • Авторизация настроена правильно")
            logger.info("  • Программа Wildberries подключена")
            return True
        else:
            logger.error("\n✗ Не удалось создать deeplink")
            logger.info("\n  Возможные причины:")
            logger.info("  1. Неверный ADMITAD_AUTH_HEADER")
            logger.info("     → Проверьте что скопировали всю строку из личного кабинета")
            logger.info("     → Убедитесь что добавили префикс 'Basic ' перед закодированной частью")
            logger.info("  2. Неверный ADMITAD_WEBSITE_ID")
            logger.info("     → Должен совпадать с client_id из учетных данных API")
            logger.info("  3. Площадка не одобрена в Admitad")
            logger.info("     → Зайдите в личный кабинет и проверьте статус площадки")
            logger.info("  4. Не подключена программа Wildberries")
            logger.info("     → В разделе 'Партнерские программы' найдите Wildberries")
            logger.info("     → Подайте заявку на подключение если еще не сделали")
            logger.info("\n  Проверьте логи выше - там могут быть детали ошибки от API")
            return False
            
    except Exception as e:
        logger.error(f"\n✗ Критическая ошибка при тестировании Admitad: {e}", exc_info=True)
        return False


async def test_affiliate_manager():
    """
    Тест работы AffiliateManager.
    
    Проверяет:
    1. Инициализацию менеджера
    2. Определение магазина по URL
    3. Генерацию партнерских ссылок для разных магазинов
    """
    logger.info("="*60)
    logger.info("ТЕСТ: Работа AffiliateManager")
    logger.info("="*60)
    
    try:
        # Создаем менеджер
        manager = AffiliateManager({
            'ADMITAD_AUTH_HEADER': settings.ADMITAD_AUTH_HEADER,
            'ADMITAD_WEBSITE_ID': settings.ADMITAD_WEBSITE_ID
        })
        
        logger.info("✓ AffiliateManager инициализирован")
        logger.info(f"  Поддерживаемые магазины: {', '.join(manager.supported_shops)}")
        
        # Тестовые URL разных магазинов
        test_urls = {
            'Wildberries': 'https://www.wildberries.ru/catalog/12345678/detail.aspx',
            'Ozon': 'https://www.ozon.ru/product/123456/',
            'Lamoda': 'https://www.lamoda.ru/p/12345678/',
            'MVideo': 'https://www.mvideo.ru/products/12345678',
        }
        
        logger.info("\nТестирование определения магазинов:")
        for shop_name, url in test_urls.items():
            detected_shop = manager.detect_shop_from_url(url)
            if detected_shop:
                logger.info(f"  ✓ {shop_name}: {detected_shop}")
            else:
                logger.warning(f"  ✗ {shop_name}: не распознан")
        
        logger.info("\n✓ Менеджер работает корректно")
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Ошибка при тестировании менеджера: {e}", exc_info=True)
        return False


async def run_all_tests():
    """Запуск всех тестов последовательно."""
    logger.info("\n")
    logger.info("="*60)
    logger.info("ТЕСТИРОВАНИЕ ПАРТНЕРСКИХ ПРОГРАММ")
    logger.info("Версия: Только Admitad")
    logger.info("="*60)
    
    # Проверяем наличие настроек перед началом
    if not settings.ADMITAD_AUTH_HEADER or not settings.ADMITAD_WEBSITE_ID:
        logger.error("\n✗ КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют настройки Admitad в .env файле")
        logger.info("\nСоздайте файл .env в корне проекта со следующим содержимым:")
        logger.info("BOT_TOKEN=ваш_токен_бота")
        logger.info("ADMITAD_AUTH_HEADER=Basic ваш_base64_токен")
        logger.info("ADMITAD_WEBSITE_ID=ваш_website_id")
        return False
    
    results = []
    
    # Запускаем тесты
    logger.info(f"Запуск теста 1 из 2...")
    results.append(("Подключение к Admitad", await test_admitad_connection()))
    
    logger.info(f"\nЗапуск теста 2 из 2...")
    results.append(("Работа AffiliateManager", await test_affiliate_manager()))
    
    # Выводим итоги
    logger.info("\n")
    logger.info("="*60)
    logger.info("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("="*60)
    logger.info(f"Пройдено тестов: {passed}/{total}")
    logger.info("="*60)
    
    if passed == total:
        logger.info("\n🎉 Все тесты пройдены успешно!")
        logger.info("Партнерская программа Admitad готова к использованию.")
    else:
        logger.warning("\n⚠️  Некоторые тесты не пройдены.")
        logger.info("Проверьте логи выше для диагностики проблем.")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nТестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nКритическая ошибка при выполнении тестов: {e}")
        logger.error("Пожалуйста сообщите об этой ошибке разработчику")
        sys.exit(1)
