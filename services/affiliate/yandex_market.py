"""
Сервис для работы с Yandex Market партнерской программой.

Прямая интеграция с Яндекс.Маркет через их Affiliate API.
"""

import logging
import aiohttp
from typing import Optional, Dict, Any

from .base import AffiliateServiceBase

logger = logging.getLogger(__name__)


class YandexMarketService(AffiliateServiceBase):
    """
    Сервис для генерации партнерских ссылок Яндекс.Маркет.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.network_name = "yandex_market"
        
        self.campaign_id = config.get('campaign_id')
        self.api_key = config.get('api_key')
        
        self.base_url = "https://api.partner.market.yandex.ru/v2"
    
    async def generate_affiliate_link(
        self, 
        original_url: str, 
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует партнерскую ссылку для Яндекс.Маркет.
        
        Примечание: API Яндекс.Маркет требует offer_id,
        который нужно извлечь из URL.
        """
        if not self.is_configured():
            logger.warning("Yandex Market не настроен")
            return None
        
        try:
            # Извлекаем offer_id из URL
            # Пример URL: https://market.yandex.ru/product--nazvanie/123456
            offer_id = self._extract_offer_id(original_url)
            if not offer_id:
                logger.error("Не удалось извлечь offer_id из URL")
                return None
            
            headers = {
                'Authorization': f'OAuth oauth_token="{self.api_key}"',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'offers': [
                    {
                        'offerId': offer_id,
                        'params': {
                            'clid': str(user_id)  # Tracking parameter
                        }
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/campaigns/{self.campaign_id}/offer-urls',
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        urls = data.get('result', {}).get('offerUrls', [])
                        
                        if urls:
                            affiliate_url = urls[0].get('url')
                            logger.info(f"✓ Yandex Market ссылка создана для user {user_id}")
                            return affiliate_url
                        else:
                            logger.error("URL не найден в ответе")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка Yandex API: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение Yandex Market: {e}", exc_info=True)
            return None
    
    def _extract_offer_id(self, url: str) -> Optional[str]:
        """
        Извлекает offer_id из URL Яндекс.Маркет.
        
        Упрощенная реализация - в реальности нужен более надежный парсинг.
        """
        import re
        
        # Паттерн для извлечения ID из URL
        pattern = r'/product--[\w-]+/(\d+)'
        match = re.search(pattern, url)
        
        if match:
            return match.group(1)
        
        return None
    
    async def check_order_status(
        self, 
        link_id: int,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверяет статистику по ссылке через Yandex API.
        """
        if not self.is_configured():
            return {'status': 'error', 'message': 'Not configured'}
        
        try:
            headers = {
                'Authorization': f'OAuth oauth_token="{self.api_key}"'
            }
            
            # Получаем статистику кампании
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.base_url}/campaigns/{self.campaign_id}/stats',
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Обрабатываем статистику
                        # TODO: Детальный парсинг статистики
                        
                        return {
                            'status': 'pending',
                            'amount': 0,
                            'cashback_amount': 0,
                            'details': data
                        }
                    else:
                        logger.error(f"Ошибка статистики: {response.status}")
                        return {'status': 'error'}
                        
        except Exception as e:
            logger.error(f"Ошибка check_order_status: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    async def get_cashback_percent(self, shop: str, category: str) -> int:
        """
        Yandex Market обычно дает 3-5% кэшбэка.
        """
        return 4  # Средний процент