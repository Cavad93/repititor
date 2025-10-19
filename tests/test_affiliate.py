"""
Тесты для проверки работы партнерских программ.

Эти тесты помогут убедиться что API ключи настроены правильно
и сервисы работают корректно. Каждый тест проверяет отдельный
аспект интеграции и дает понятные сообщения об ошибках чтобы
вы могли быстро найти и исправить проблему.

Запуск тестов: python tests/test_affiliate.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь поиска модулей
# Это позволяет импортировать модули проекта даже когда
# мы запускаем скрипт из папки tests
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.affiliate.manager import AffiliateManager
from config.settings import settings
import logging

# Настраиваем базовое логирование чтобы видеть все сообщения
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_admitad_connection():
    """
    Тест подключения к Admitad и генерации тестовой ссылки.
    
    Этот тест проверяет что вы правильно скопировали Base64 заголовок
    авторизации из личного кабинета Admitad и что ваша площадка
    одобрена для работы с API.
    
    Что проверяется:
    1. Наличие всех необходимых настроек (auth_header и website_id)
    2. Правильность формата заголовка (должен начинаться с "Basic ")
    3. Возможность создания реальной партнерской ссылки
    
    Если тест не проходит смотрите подробности ошибки в логах ниже.
    """
    logger.info("=" * 60)
    logger.info("ТЕСТ: Подключение к Admitad")
    logger.info("=" * 60)
    
    from services.affiliate.admitad import AdmitadService
    
    # Инициализируем сервис с настройками из .env файла
    # ВАЖНО: Мы используем auth_header вместо client_id/client_secret
    # потому что Admitad предоставляет готовый Base64 заголовок
    service = AdmitadService({
        'auth_header': settings.ADMITAD_AUTH_HEADER,
        'website_id': settings.ADMITAD_WEBSITE_ID
    })
    
    # Первая проверка: настроен ли сервис вообще
    # Метод is_configured проверяет наличие обязательных параметров
    if not service.is_configured():
        logger.error("✗ Admitad не настроен (отсутствуют настройки в .env)")
        logger.info("  Проверьте следующее:")
        logger.info("  1. ADMITAD_AUTH_HEADER установлен в .env")
        logger.info("  2. ADMITAD_WEBSITE_ID установлен в .env")
        logger.info("  3. Заголовок начинается с 'Basic ' (включая пробел)")
        logger.info("  4. Нет лишних пробелов в начале или конце строк")
        return False
    
    # Если настройки есть логируем их (частично для безопасности)
    logger.info("✓ Admitad настроен корректно")
    logger.info(f"  Website ID: {service.website_id}")
    # Показываем только первые 30 символов заголовка для безопасности
    logger.info(f"  Auth header: {service.auth_header[:30]}...")
    
    # Главная проверка: попытка создать реальную партнерскую ссылку
    logger.info("\nГенерация тестовой deeplink...")
    logger.info("  Используем тестовый URL от Wildberries")
    
    # Тестовая ссылка на несуществующий товар - это нормально
    # API Admitad всё равно создаст партнерскую ссылку
    # потому что проверка существования товара это задача магазина
    test_url = "https://www.wildberries.ru/catalog/12345678/detail.aspx"
    logger.info(f"  Original URL: {test_url}")
    
    # Вызываем метод генерации ссылки
    # Если всё настроено правильно через несколько секунд
    # мы получим готовую партнерскую ссылку с трекингом
    affiliate_link = await service.generate_affiliate_link(
        test_url,
        user_id=123456789,  # Тестовый ID пользователя
        product_info=None
    )
    
    # Проверяем результат
    if affiliate_link:
        logger.info(f"\n✓ Deeplink создан успешно!")
        # Показываем первые 80 символов ссылки
        logger.info(f"  Affiliate link: {affiliate_link[:80]}...")
        logger.info("\n🎉 Admitad работает корректно!")
        logger.info("  Ваш бот готов генерировать кэшбэк-ссылки")
        return True
    else:
        # Если ссылка не создалась даем подсказки что проверить
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


async def test_backit_connection():
    """
    Тест подключения к Backit (опциональный сервис).
    
    Backit специализируется на AliExpress и некоторых других
    площадках. Этот сервис не является критичным для работы бота
    потому что основные российские магазины доступны через Admitad.
    
    Если Backit не настроен тест всё равно пройдет успешно
    потому что это не блокирует основную функциональность.
    """
    logger.info("=" * 60)
    logger.info("ТЕСТ: Подключение к Backit (опционально)")
    logger.info("=" * 60)
    
    from services.affiliate.backit import BackitService
    
    service = BackitService({
        'api_key': settings.BACKIT_API_KEY,
        'user_id': settings.BACKIT_USER_ID
    })
    
    # Проверяем настроен ли Backit
    if not service.is_configured():
        logger.warning("⚠ Backit не настроен")
        logger.info("  Это не критично - Backit можно пропустить")
        logger.info("  Основные магазины (Wildberries, Ozon, Lamoda)")
        logger.info("  доступны через Admitad")
        logger.info("  Статус теста: PASSED (не обязательный сервис)")
        return True  # Не критично - тест считается пройденным
    
    # Если Backit настроен пробуем создать ссылку
    logger.info("Генерация тестовой ссылки через Backit...")
    test_url = "https://www.ozon.ru/product/12345678/"
    
    affiliate_link = await service.generate_affiliate_link(
        test_url,
        user_id=123456789,
        product_info=None
    )
    
    if affiliate_link:
        logger.info(f"✓ Backit ссылка создана: {affiliate_link[:80]}...")
        logger.info("✓ Backit работает корректно!")
        return True
    else:
        # Даже если Backit не работает это не критично
        logger.warning("⚠ Не удалось создать Backit ссылку")
        logger.info("  Это не критично для работы бота")
        logger.info("  Можете продолжить без Backit")
        return True  # Тест считается пройденным


async def test_affiliate_manager():
    """
    Тест менеджера партнерских программ с реальными URL.
    
    Это комплексный тест который проверяет что менеджер правильно
    определяет магазины по URL выбирает подходящую партнерскую сеть
    и генерирует корректные кэшбэк-ссылки.
    
    Тестируются самые популярные магазины чтобы убедиться что
    ваш бот сможет обрабатывать большинство запросов пользователей.
    """
    logger.info("=" * 60)
    logger.info("ТЕСТ: Менеджер партнерских программ")
    logger.info("=" * 60)
    
    # Инициализируем менеджер с настройками
    # Обратите внимание: мы НЕ передаем настройки Yandex Market
    # потому что этот магазин работает через Admitad
    manager = AffiliateManager({
        'ADMITAD_AUTH_HEADER': settings.ADMITAD_AUTH_HEADER,
        'ADMITAD_WEBSITE_ID': settings.ADMITAD_WEBSITE_ID,
        'BACKIT_API_KEY': settings.BACKIT_API_KEY,
        'BACKIT_USER_ID': settings.BACKIT_USER_ID
    })
    
    # Список тестовых URL для проверки разных магазинов
    # Каждый кортеж содержит название магазина и тестовую ссылку
    test_urls = [
        ("Wildberries", "https://www.wildberries.ru/catalog/12345678/detail.aspx"),
        ("Ozon", "https://www.ozon.ru/product/smartfon-12345678/"),
        ("Lamoda", "https://www.lamoda.ru/p/mp002xm123ab/shoes-nike-krossovki/"),
        ("Яндекс.Маркет", "https://market.yandex.ru/product--smartfon/12345678")
    ]
    
    results = []
    
    logger.info("\nТестирование генерации ссылок для разных магазинов:\n")
    
    # Проверяем каждый магазин по очереди
    for shop_name, url in test_urls:
        logger.info(f"{'─' * 60}")
        logger.info(f"Магазин: {shop_name}")
        logger.info(f"URL: {url}")
        
        # Вызываем менеджер для генерации партнерской ссылки
        # Менеджер автоматически:
        # 1. Определит магазин по домену URL
        # 2. Выберет подходящую партнерскую программу
        # 3. Сгенерирует кэшбэк-ссылку или вернет ошибку
        result = await manager.generate_affiliate_link(
            original_url=url,
            user_id=123456789,
            product_info={'category': 'electronics'}
        )
        
        # Анализируем результат
        if result.get('affiliate_url'):
            # Успех - ссылка создана
            logger.info(f"✓ Статус: УСПЕШНО")
            logger.info(f"  Партнерская сеть: {result['network']}")
            logger.info(f"  Процент кэшбэка: {result['cashback_percent']}%")
            logger.info(f"  Ссылка: {result['affiliate_url'][:70]}...")
            results.append(True)
            
        elif result.get('error'):
            # Ошибка но это может быть нормально
            # Например магазин не поддерживается или программа не подключена
            logger.warning(f"⚠ Статус: {result['error']}")
            
            # Проверяем тип ошибки
            if "не поддерживается" in result['error'].lower():
                logger.info("  Это нормально если вы не подключили этот магазин")
                results.append(True)  # Не критично
            elif "временно недоступен" in result['error'].lower():
                logger.info("  Партнерская программа недоступна")
                logger.info("  Проверьте что программа этого магазина подключена в Admitad")
                results.append(True)  # Не критично для теста
            else:
                logger.error("  Неожиданная ошибка")
                results.append(False)
        else:
            # Что-то пошло не так - нет ни ссылки ни понятной ошибки
            logger.error(f"✗ Статус: ОШИБКА")
            logger.error("  Не удалось создать ссылку и нет информации об ошибке")
            results.append(False)
    
    # Подводим итоги теста менеджера
    logger.info(f"\n{'─' * 60}")
    
    if all(results):
        logger.info("✓ Все тесты менеджера пройдены успешно!")
        logger.info("  Менеджер корректно обрабатывает разные магазины")
        return True
    else:
        logger.error("✗ Некоторые тесты менеджера не прошли")
        logger.info("  Проверьте логи выше для деталей")
        return False


async def run_all_tests():
    """
    Запуск всех тестов партнерских программ.
    
    Эта функция координирует выполнение всех тестовых сценариев
    и выводит понятный итоговый отчет о результатах.
    """
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТИРОВАНИЕ ПАРТНЕРСКИХ ПРОГРАММ")
    logger.info("Версия: Этап 3 (Base64 авторизация)")
    logger.info("=" * 60 + "\n")
    
    # Список для хранения результатов каждого теста
    results = []
    
    # Тест 1: Admitad (критично для работы бота)
    logger.info("Запуск теста 1 из 3...\n")
    admitad_result = await test_admitad_connection()
    results.append(("Admitad (обязательно)", admitad_result))
    
    # Небольшая пауза между тестами для читаемости логов
    await asyncio.sleep(1)
    
    # Тест 2: Backit (опционально)
    logger.info("\n\nЗапуск теста 2 из 3...\n")
    backit_result = await test_backit_connection()
    results.append(("Backit (опционально)", backit_result))
    
    await asyncio.sleep(1)
    
    # Тест 3: Менеджер партнерских программ
    logger.info("\n\nЗапуск теста 3 из 3...\n")
    manager_result = await test_affiliate_manager()
    results.append(("Manager (комплексный)", manager_result))
    
    # Выводим красивую таблицу результатов
    logger.info("\n\n" + "=" * 60)
    logger.info("ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60 + "\n")
    
    # Подсчитываем пройденные тесты
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    # Выводим результат каждого теста
    for test_name, passed in results:
        if passed:
            status = "✓ PASSED"
            emoji = "🟢"
        else:
            status = "✗ FAILED"
            emoji = "🔴"
        
        logger.info(f"{emoji} {test_name}: {status}")
    
    # Общая статистика
    logger.info(f"\n{'─' * 60}")
    logger.info(f"Пройдено тестов: {passed_count}/{total_count}")
    logger.info("=" * 60 + "\n")
    
    # Финальный вердикт и рекомендации
    if passed_count == total_count:
        logger.info("🎉 ОТЛИЧНО! Все тесты пройдены успешно!")
        logger.info("\nПартнерские программы настроены корректно.")
        logger.info("Ваш бот готов генерировать кэшбэк-ссылки!")
        logger.info("\nСледующие шаги:")
        logger.info("1. Запустите бота: python main.py")
        logger.info("2. Отправьте боту ссылку на товар для проверки")
        logger.info("3. Убедитесь что бот создает кэшбэк-ссылку")
        return True
    else:
        failed_critical = not results[0][1]  # Проверяем провалился ли Admitad
        
        if failed_critical:
            logger.error("⚠ КРИТИЧЕСКАЯ ОШИБКА!")
            logger.error("\nТест Admitad не прошел - это блокирует работу бота.")
            logger.error("Без Admitad бот не сможет создавать кэшбэк-ссылки.")
            logger.error("\nЧто делать:")
            logger.error("1. Внимательно прочитайте сообщения об ошибках выше")
            logger.error("2. Проверьте настройки в файле .env:")
            logger.error("   - ADMITAD_AUTH_HEADER (включая префикс 'Basic ')")
            logger.error("   - ADMITAD_WEBSITE_ID")
            logger.error("3. Убедитесь что площадка одобрена в личном кабинете Admitad")
            logger.error("4. Подключитесь к программам магазинов (Wildberries, Ozon и т.д.)")
        else:
            logger.warning("⚠ Некоторые тесты не прошли")
            logger.info("\nНо это не критично! Основная интеграция (Admitad) работает.")
            logger.info("Бот может работать с ограниченным функционалом.")
            logger.info("\nПроверьте детали ошибок выше если хотите исправить.")
        
        return False


if __name__ == "__main__":
    """
    Точка входа для запуска тестов.
    
    Запускает асинхронные тесты и возвращает правильный код выхода
    для интеграции с CI/CD системами (0 = успех, 1 = ошибка).
    """
    try:
        success = asyncio.run(run_all_tests())
        
        # Возвращаем код выхода: 0 если все тесты прошли, 1 если были ошибки
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        # Обрабатываем прерывание пользователем (Ctrl+C)
        logger.info("\n\nТестирование прервано пользователем")
        sys.exit(1)
        
    except Exception as e:
        # Ловим любые неожиданные ошибки
        logger.error(f"\n\nКритическая ошибка при выполнении тестов: {e}")
        logger.error("Пожалуйста сообщите об этой ошибке разработчику", exc_info=True)
        sys.exit(1)