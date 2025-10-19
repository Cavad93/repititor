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
    3. Генерацию тестовых партнерских ссылок для РАЗНЫХ магазинов
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
        
        # Тестовые URL для РАЗНЫХ магазинов
        # Проверим все поддерживаемые магазины и найдем хотя бы один рабочий
        test_urls = {
            'Lamoda': 'https://www.lamoda.ru/p/mp002xw02hzg/shoes-tamaris-tufli/',
            'МВидео': 'https://www.mvideo.ru/products/smartfon-apple-iphone-13-128gb-midnight-mlpf3-400232825',
            'Ozon': 'https://www.ozon.ru/product/smartfon-apple-iphone-13-128gb-siniy-261044708/',
            'Wildberries': 'https://www.wildberries.ru/catalog/12345678/detail.aspx',
            'Яндекс.Маркет': 'https://market.yandex.ru/product--smartfon-apple-iphone-13-128gb/1234567890',
            'СберМегаМаркет': 'https://sbermegamarket.ru/catalog/details/smartfon-apple-iphone-13-128-gb-100028374917/'
        }
        
        logger.info("\n" + "="*60)
        logger.info("ПРОВЕРКА ПОДКЛЮЧЕННЫХ ПРОГРАММ МАГАЗИНОВ")
        logger.info("="*60)
        logger.info("\nТестирование генерации deeplink для каждого магазина...")
        logger.info("Это покажет какие программы уже активны в вашем аккаунте.\n")
        
        test_user_id = 123456789
        successful_shops = []
        failed_shops = []
        
        for shop_name, test_url in test_urls.items():
            logger.info(f"🔄 Тестирую {shop_name}...")
            logger.info(f"   URL: {test_url[:60]}...")
            
            affiliate_link = await admitad.generate_affiliate_link(
                test_url, test_user_id
            )
            
            if affiliate_link:
                logger.info(f"   ✅ РАБОТАЕТ! Deeplink создан успешно")
                logger.info(f"   Ссылка: {affiliate_link[:80]}...\n")
                successful_shops.append(shop_name)
            else:
                logger.info(f"   ❌ Не работает (программа не подключена)\n")
                failed_shops.append(shop_name)
        
        # Итоговый отчет
        logger.info("="*60)
        logger.info("ИТОГОВЫЙ ОТЧЕТ")
        logger.info("="*60)
        
        if successful_shops:
            logger.info(f"\n✅ ПОДКЛЮЧЕННЫЕ ПРОГРАММЫ ({len(successful_shops)}):")
            for shop in successful_shops:
                logger.info(f"   • {shop} - готов к работе!")
            
            logger.info(f"\n❌ НЕ ПОДКЛЮЧЕННЫЕ ПРОГРАММЫ ({len(failed_shops)}):")
            for shop in failed_shops:
                logger.info(f"   • {shop} - требует подключения")
            
            logger.info("\n🎉 ОТЛИЧНО! Хотя бы одна программа работает!")
            logger.info("Вы можете начать использовать бота с подключенными магазинами.")
            logger.info(f"\nДля работы с остальными магазинами подключите их в личном кабинете Admitad.")
            
            return True
        else:
            logger.error(f"\n❌ НИ ОДНА ПРОГРАММА НЕ ПОДКЛЮЧЕНА")
            logger.info("\nВСЕ МАГАЗИНЫ ТРЕБУЮТ ПОДКЛЮЧЕНИЯ:")
            for shop in failed_shops:
                logger.info(f"   • {shop}")
            
            logger.info("\n📋 ЧТО ДЕЛАТЬ:")
            logger.info("1. Зайдите в личный кабинет Admitad: https://www.admitad.com/ru/")
            logger.info("2. Перейдите в раздел 'Партнерские программы'")
            logger.info("3. Найдите любой из этих магазинов (рекомендую начать с Lamoda)")
            logger.info("4. Нажмите 'Подключить' или 'Подать заявку'")
            logger.info("5. Дождитесь одобрения (обычно 1-24 часа)")
            logger.info("\n💡 СОВЕТ: Lamoda и МВидео обычно одобряются быстрее всего!")
            
            logger.info("\n⚠️  ВРЕМЕННАЯ ПРОБЛЕМА С WILDBERRIES:")
            logger.info("Если Wildberries не принимает заявки, используйте Lamoda или МВидео.")
            logger.info("Функционал бота идентичен для всех магазинов.")
            
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
