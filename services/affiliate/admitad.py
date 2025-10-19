"""
Сервис для работы с Admitad партнерской программой.

Admitad - крупнейшая CPA-сеть с интеграцией Wildberries, Ozon, Lamoda и др.
"""

import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from .base import AffiliateServiceBase

logger = logging.getLogger(__name__)


class AdmitadService(AffiliateServiceBase):
    """
    Сервис для генерации партнерских ссылок через Admitad.
    
    Использует OAuth2 для аутентификации и Deeplink API для генерации ссылок.
    
    ВАЖНО: Для работы нужны:
    - ADMITAD_CLIENT_ID
    - ADMITAD_CLIENT_SECRET  
    - ADMITAD_WEBSITE_ID
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.network_name = "admitad"
        
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.website_id = config.get('website_id')
        
        self.access_token = None
        self.token_expires_at = 0
        
        # URL эндпоинтов Admitad API
        self.auth_url = "https://api.admitad.com/token/"
        self.deeplink_url = "https://api.admitad.com/deeplink/gen/"
        self.statistics_url = "https://api.admitad.com/statistics/sub_ids/"
    
    async def _get_access_token(self) -> Optional[str]:
        """
        Получает access_token через OAuth2.
        
        Токен кэшируется и обновляется только при истечении.
        """
        import time
        
        # Проверяем не истек ли кэшированный токен
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        logger.info("Получение нового access_token от Admitad")
        
        try:
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'deeplink_generator statistics'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.auth_url, data=auth_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.access_token = data['access_token']
                        # Токен действителен 1 час, кэшируем на 50 минут
                        self.token_expires_at = time.time() + 3000
                        
                        logger.info("✓ Access token получен")
                        return self.access_token
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения токена: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение при получении токена: {e}", exc_info=True)
            return None
    
    async def generate_affiliate_link(
        self, 
        original_url: str, 
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует deeplink через Admitad API.
        
        Args:
            original_url: Ссылка на товар (например, https://www.wildberries.ru/...)
            user_id: Telegram ID пользователя
            product_info: Информация о товаре (не используется Admitad API)
            
        Returns:
            str: Партнерская ссылка с трекингом
        """
        if not self.is_configured():
            logger.warning("Admitad не настроен (отсутствуют API ключи)")
            return None
        
        token = await self._get_access_token()
        if not token:
            logger.error("Не удалось получить access_token")
            return None
        
        try:
            # Формируем subid для отслеживания (user_id + timestamp)
            import time
            subid = f"tg_{user_id}_{int(time.time())}"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            params = {
                'ulp': original_url,  # URL товара
                'sub_id': subid       # Идентификатор для отслеживания
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.deeplink_url,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        affiliate_link = data.get('deeplink')
                        
                        if affiliate_link:
                            logger.info(f"✓ Deeplink создан для user {user_id}")
                            return affiliate_link
                        else:
                            logger.error("Deeplink не найден в ответе API")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка создания deeplink: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение при генерации deeplink: {e}", exc_info=True)
            return None
    
    async def check_order_status(
        self, 
        link_id: int,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверяет статус заказов через Statistics API.
        
        Admitad предоставляет статистику по subid, поэтому
        мы можем отследить все заказы пользователя.
        """
        if not self.is_configured():
            return {'status': 'error', 'message': 'Service not configured'}
        
        token = await self._get_access_token()
        if not token:
            return {'status': 'error', 'message': 'Failed to get token'}
        
        try:
            # Загружаем link из БД чтобы получить subid
            from database.connection import async_session_maker
            from database.models import AffiliateLink
            from sqlalchemy import select
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(AffiliateLink).where(AffiliateLink.link_id == link_id)
                )
                link = result.scalar_one_or_none()
                
                if not link:
                    return {'status': 'error', 'message': 'Link not found'}
                
                # Извлекаем subid из параметров ссылки
                # TODO: Сохранять subid при создании ссылки
                
            # Запрашиваем статистику по subid
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            # Пример запроса статистики (упрощенный)
            # В реальности нужно фильтровать по датам и subid
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.statistics_url,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Обрабатываем данные статистики
                        # TODO: Полная реализация парсинга статистики
                        
                        return {
                            'status': 'pending',
                            'amount': 0,
                            'cashback_amount': 0,
                            'details': data
                        }
                    else:
                        logger.error(f"Ошибка получения статистики: {response.status}")
                        return {'status': 'error', 'message': 'API error'}
                        
        except Exception as e:
            logger.error(f"Ошибка проверки статуса: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    async def get_cashback_percent(self, shop: str, category: str) -> int:
        """
        Возвращает процент кэшбэка для магазина.
        
        В Admitad проценты зависят от программы магазина.
        Здесь используются типичные значения.
        """
        # Типичные проценты для популярных магазинов в Admitad
        cashback_rates = {
            'wildberries': 5,
            'ozon': 4,
            'lamoda': 7,
            'mvideo': 3,
            'detmir': 6
        }
        
        return cashback_rates.get(shop, 3)  # По умолчанию 3%