"""
Сервис для работы с Admitad партнерской программой.

Admitad - крупнейшая CPA-сеть с интеграцией Wildberries, Ozon, Lamoda и др.
Использует Base64 авторизацию вместо OAuth.
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from .base import AffiliateServiceBase

logger = logging.getLogger(__name__)


class AdmitadService(AffiliateServiceBase):
    """
    Сервис для генерации партнерских ссылок через Admitad.
    
    Использует Base64 заголовок авторизации для аутентификации.
    Это упрощенная альтернатива OAuth которую Admitad предоставляет
    для серверных приложений.
    
    ВАЖНО: Для работы нужны:
    - ADMITAD_AUTH_HEADER (включая префикс 'Basic ')
    - ADMITAD_WEBSITE_ID
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.network_name = "admitad"
        
        # Получаем готовый заголовок авторизации
        self.auth_header = config.get('auth_header')
        self.website_id = config.get('website_id')
        
        # URL эндпоинтов Admitad API
        self.deeplink_url = "https://api.admitad.com/deeplink/gen/"
        self.statistics_url = "https://api.admitad.com/statistics/sub_ids/"
    
    def is_configured(self) -> bool:
        """
        Проверяет что сервис настроен правильно.
        
        Для работы необходимы заголовок авторизации и ID площадки.
        """
        if not self.auth_header:
            logger.warning("ADMITAD_AUTH_HEADER не установлен в настройках")
            return False
        
        if not self.website_id:
            logger.warning("ADMITAD_WEBSITE_ID не установлен в настройках")
            return False
        
        # Проверяем что заголовок начинается с "Basic "
        if not self.auth_header.startswith('Basic '):
            logger.warning(
                "ADMITAD_AUTH_HEADER должен начинаться с 'Basic ' "
                "(включая пробел после Basic)"
            )
            return False
        
        return True
    
    async def generate_affiliate_link(
        self, 
        original_url: str, 
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует deeplink через Admitad API.
        
        Процесс работы:
        1. Берем оригинальную ссылку на товар
        2. Добавляем к ней уникальный идентификатор пользователя (subid)
        3. Отправляем запрос к Admitad API с этими данными
        4. Получаем обратно партнерскую ссылку с трекингом
        
        Args:
            original_url: Ссылка на товар (например, https://www.wildberries.ru/...)
            user_id: Telegram ID пользователя
            product_info: Информация о товаре (не используется в этом API)
            
        Returns:
            str: Партнерская ссылка с трекингом или None при ошибке
        """
        if not self.is_configured():
            logger.error("Admitad не настроен - проверьте .env файл")
            return None
        
        try:
            # Формируем уникальный subid для отслеживания
            # Формат: tg_<user_id>_<timestamp>
            # Это позволит нам понять какой пользователь совершил покупку
            import time
            subid = f"tg_{user_id}_{int(time.time())}"
            
            logger.info(f"Создание deeplink для пользователя {user_id}")
            logger.debug(f"Original URL: {original_url}")
            logger.debug(f"SubID: {subid}")
            
            # Заголовки запроса
            # Authorization содержит наш готовый Base64 токен
            headers = {
                'Authorization': self.auth_header,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Параметры для API
            params = {
                'ulp': original_url,  # URL товара (ulp = ultimate landing page)
                'sub_id': subid       # Идентификатор для отслеживания
            }
            
            # Отправляем GET запрос к API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.deeplink_url,
                    headers=headers,
                    params=params
                ) as response:
                    
                    # Проверяем статус ответа
                    if response.status == 200:
                        data = await response.json()
                        affiliate_link = data.get('deeplink')
                        
                        if affiliate_link:
                            logger.info(
                                f"✓ Deeplink создан успешно для user {user_id}"
                            )
                            logger.debug(f"Affiliate link: {affiliate_link[:80]}...")
                            return affiliate_link
                        else:
                            logger.error("Deeplink не найден в ответе API")
                            logger.debug(f"Response data: {data}")
                            return None
                    
                    elif response.status == 401:
                        # Ошибка авторизации - неверный заголовок
                        logger.error(
                            "Ошибка авторизации (401). "
                            "Проверьте правильность ADMITAD_AUTH_HEADER"
                        )
                        error_text = await response.text()
                        logger.debug(f"Error response: {error_text}")
                        return None
                    
                    elif response.status == 403:
                        # Доступ запрещен - возможно площадка не одобрена
                        logger.error(
                            "Доступ запрещен (403). "
                            "Проверьте что площадка одобрена в Admitad "
                            "и программа магазина подключена"
                        )
                        error_text = await response.text()
                        logger.debug(f"Error response: {error_text}")
                        return None
                    
                    elif response.status == 404:
                        # Программа не найдена - магазин не поддерживается
                        logger.warning(
                            f"Программа для этого магазина не найдена (404). "
                            f"URL: {original_url}"
                        )
                        return None
                    
                    else:
                        # Другая ошибка
                        error_text = await response.text()
                        logger.error(
                            f"Ошибка API Admitad: {response.status} - {error_text}"
                        )
                        return None
                        
        except aiohttp.ClientError as e:
            # Ошибка сети - например нет интернета
            logger.error(f"Ошибка сети при обращении к Admitad: {e}")
            return None
        
        except Exception as e:
            # Любая другая непредвиденная ошибка
            logger.error(f"Непредвиденная ошибка при генерации deeplink: {e}", exc_info=True)
            return None
    
    async def check_order_status(
        self, 
        link_id: int,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверяет статус заказов через Statistics API.
        
        Admitad предоставляет статистику по subid, поэтому
        мы можем отследить все заказы конкретного пользователя.
        
        Статусы заказов в Admitad:
        - pending: Ожидает подтверждения магазином
        - confirmed: Подтвержден магазином, кэшбэк будет выплачен
        - rejected: Отклонен (возврат, отмена заказа и т.д.)
        """
        if not self.is_configured():
            return {
                'status': 'error', 
                'message': 'Service not configured'
            }
        
        try:
            # Загружаем информацию о ссылке из базы данных
            from database.connection import async_session_maker
            from database.models import AffiliateLink
            from sqlalchemy import select
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(AffiliateLink).where(AffiliateLink.link_id == link_id)
                )
                link = result.scalar_one_or_none()
                
                if not link:
                    return {
                        'status': 'error', 
                        'message': 'Link not found in database'
                    }
                
                # TODO: Извлечь subid из product_info или из URL
                # Для полной реализации нужно сохранять subid при создании ссылки
            
            # Заголовки для Statistics API
            headers = {
                'Authorization': self.auth_header
            }
            
            # Запрашиваем статистику
            # Упрощенная версия - полная реализация требует
            # фильтрации по датам и subid
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.statistics_url,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # В реальной реализации нужно парсить статистику
                        # и находить конкретный заказ по subid
                        # Пока возвращаем pending как заглушку
                        
                        return {
                            'status': 'pending',
                            'amount': 0,
                            'cashback_amount': 0,
                            'details': 'Statistics API implementation in progress'
                        }
                    
                    else:
                        logger.error(
                            f"Ошибка получения статистики: {response.status}"
                        )
                        return {
                            'status': 'error',
                            'message': f'API error: {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"Ошибка проверки статуса заказа: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def get_cashback_percent(self, shop: str, category: str) -> int:
        """
        Возвращает типичный процент кэшбэка для магазина.
        
        В Admitad проценты варьируются в зависимости от программы
        и категории товаров. Здесь используются средние значения
        для популярных российских магазинов.
        
        Args:
            shop: Название магазина (wildberries, ozon, etc.)
            category: Категория товара (может влиять на процент)
            
        Returns:
            int: Процент кэшэка (например, 5 означает 5%)
        """
        # Типичные проценты кэшбэка в Admitad для популярных магазинов
        cashback_rates = {
            'wildberries': 5,   # Wildberries обычно 4-6%
            'ozon': 4,          # Ozon обычно 3-5%
            'lamoda': 7,        # Lamoda часто дает высокий кэшбэк 6-8%
            'mvideo': 3,        # М.Видео обычно 2-4%
            'detmir': 6,        # Детский мир 5-7%
            'sber': 4,          # СберМегаМаркет 3-5%
            'yandex_market': 3  # Яндекс.Маркет через Admitad 2-4%
        }
        
        base_rate = cashback_rates.get(shop, 3)  # По умолчанию 3%
        
        # Некоторые категории могут давать повышенный кэшбэк
        if category in ['electronics', 'clothing']:
            base_rate += 1  # +1% для популярных категорий
        
        return base_rate
