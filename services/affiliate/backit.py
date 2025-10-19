"""
Сервис для работы с Backit (бывший ePN).

Backit специализируется на AliExpress и российских магазинах.
"""

import logging
import aiohttp
import json
from typing import Optional, Dict, Any

from .base import AffiliateServiceBase

logger = logging.getLogger(__name__)


class BackitService(AffiliateServiceBase):
    """
    Сервис для генерации кэшбэк-ссылок через Backit API.
    
    Использует простую аутентификацию по API-ключу.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.network_name = "backit"
        
        self.api_key = config.get('api_key')
        self.user_id = config.get('user_id')
        
        self.base_url = "https://api.backit.me/v1"
    
    async def generate_affiliate_link(
        self, 
        original_url: str, 
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует кэшбэк-ссылку через Backit API.
        """
        if not self.is_configured():
            logger.warning("Backit не настроен")
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'url': original_url,
                'user_id': str(user_id)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/links',
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        affiliate_link = data.get('affiliate_link')
                        
                        if affiliate_link:
                            logger.info(f"✓ Backit ссылка создана для user {user_id}")
                            return affiliate_link
                        else:
                            logger.error("Affiliate link не найден в ответе")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка Backit API: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение Backit: {e}", exc_info=True)
            return None
    
    async def check_order_status(
        self, 
        link_id: int,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверяет статус заказов через Backit API.
        """
        if not self.is_configured():
            return {'status': 'error', 'message': 'Not configured'}
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # Получаем заказы пользователя
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.base_url}/orders',
                    headers=headers,
                    params={'link_id': link_id}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        orders = data.get('orders', [])
                        
                        if orders:
                            # Берем первый заказ (предполагаем один заказ на ссылку)
                            order = orders[0]
                            
                            return {
                                'status': order.get('status', 'pending'),
                                'amount': order.get('amount', 0),
                                'cashback_amount': order.get('cashback', 0),
                                'details': order
                            }
                        else:
                            return {'status': 'pending', 'amount': 0, 'cashback_amount': 0}
                    else:
                        logger.error(f"Ошибка проверки заказов: {response.status}")
                        return {'status': 'error'}
                        
        except Exception as e:
            logger.error(f"Ошибка check_order_status: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    async def get_cashback_percent(self, shop: str, category: str) -> int:
        """
        Возвращает процент кэшбэка для Backit.
        """
        cashback_rates = {
            'aliexpress': 7,
            'ozon': 3,
            'wildberries': 4
        }
        
        return cashback_rates.get(shop, 3)