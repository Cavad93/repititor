# services/cashback/cashback_service.py

"""
Сервис для работы с кэшбэк-партнерками Admitad и EPN.
"""

import logging
import aiohttp
import base64
from typing import Dict, Optional, List
from urllib.parse import quote

from config.settings import settings

logger = logging.getLogger(__name__)


class CashbackService:
    """
    Единый интерфейс для работы с кэшбэк-партнерками.
    """
    
    def __init__(self):
        self.admitad = AdmitadService()
        self.epn = EPNService()
    
    async def get_cashback_link(
        self,
        shop: str,
        original_url: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Получает кэшбэк-ссылку для магазина.
        
        Args:
            shop: Название магазина
            original_url: Оригинальная ссылка на товар/акцию
            user_id: ID пользователя для subid
            
        Returns:
            Dict с полями: url, cashback_percent, network
        """
        # Определяем какую сеть использовать
        if self._is_marketplace(shop):
            # Для маркетплейсов используем EPN
            return await self.epn.generate_link(shop, original_url, user_id)
        else:
            # Для остальных магазинов - Admitad
            return await self.admitad.generate_link(shop, original_url, user_id)
    
    def _is_marketplace(self, shop: str) -> bool:
        """
        Проверяет является ли магазин маркетплейсом.
        """
        marketplaces = [
            'aliexpress', 'ali', 'алиэкспресс',
            'ozon', 'озон',
            'wildberries', 'wb', 'вайлдберриз',
            'lamoda', 'ламода',
            'mvideo', 'мвидео',
            'dns',
        ]
        shop_lower = shop.lower()
        return any(mp in shop_lower for mp in marketplaces)


class AdmitadService:
    """
    Работа с Admitad API.
    """
    
    def __init__(self):
        self.api_base = 'https://api.admitad.com'
        self.auth_header = settings.ADMITAD_AUTH_HEADER
        self.website_id = settings.ADMITAD_WEBSITE_ID
        
        # Маппинг магазинов к Admitad campaign ID
        self.shop_campaigns = {
            'пятерочка': '5ka_campaign_id',
            '5ka': '5ka_campaign_id',
            'перекресток': 'perekrestok_id',
            'магнит': 'magnit_id',
            'лента': 'lenta_id',
            'ашан': 'auchan_id',
            # Добавьте ваши campaign ID
        }
    
    async def generate_link(
        self,
        shop: str,
        original_url: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Генерирует партнерскую ссылку через Admitad.
        """
        if not self.auth_header or not self.website_id:
            logger.warning("Admitad не настроен (нет auth_header или website_id)")
            return None
        
        try:
            # Находим campaign для магазина
            campaign_id = self._get_campaign_id(shop)
            if not campaign_id:
                logger.warning(f"Магазин {shop} не найден в Admitad")
                return None
            
            # Формируем subid для отслеживания
            subid = f"user_{user_id}" if user_id else "bot"
            
            # URL для deeplink
            if original_url:
                deeplink_url = f"{self.api_base}/deeplink/create/"
                params = {
                    'website': self.website_id,
                    'url': original_url,
                    'subid': subid,
                }
            else:
                # Обычная партнерская ссылка
                deeplink_url = f"https://ad.admitad.com/g/{campaign_id}/?subid={subid}"
                return {
                    'url': deeplink_url,
                    'cashback_percent': 'до 5%',  # Примерное значение
                    'network': 'admitad'
                }
            
            # Выполняем запрос к API
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': self.auth_header,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                async with session.post(
                    deeplink_url,
                    headers=headers,
                    data=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'url': data.get('url') or data.get('deeplink'),
                            'cashback_percent': 'до 5%',
                            'network': 'admitad'
                        }
                    else:
                        logger.error(f"Ошибка Admitad API: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Ошибка генерации Admitad ссылки: {e}", exc_info=True)
            return None
    
    def _get_campaign_id(self, shop: str) -> Optional[str]:
        """
        Получает campaign ID для магазина.
        """
        shop_lower = shop.lower()
        return self.shop_campaigns.get(shop_lower)


class EPNService:
    """
    Работа с EPN API.
    """
    
    def __init__(self):
        self.api_base = 'https://api.epn.bz/json'
        
        # Маппинг маркетплейсов
        self.marketplace_map = {
            'aliexpress': 'aliexpress',
            'ali': 'aliexpress',
            'ozon': 'ozon',
            'wildberries': 'wildberries',
            'wb': 'wildberries',
            'lamoda': 'lamoda',
            'mvideo': 'mvideo',
        }
    
    async def generate_link(
        self,
        shop: str,
        original_url: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Генерирует партнерскую ссылку через EPN.
        
        Примечание: Для полной работы нужны EPN API ключи.
        Пока возвращаем базовую ссылку.
        """
        try:
            marketplace = self._get_marketplace(shop)
            if not marketplace:
                return None
            
            # Формируем базовую ссылку
            # В реальности здесь должен быть API запрос с вашими ключами
            subid = f"user_{user_id}" if user_id else "bot"
            
            if marketplace == 'aliexpress':
                # Для AliExpress особая логика
                if original_url:
                    encoded_url = quote(original_url, safe='')
                    partner_url = f"https://s.click.aliexpress.com/deep_link.htm?aff_short_key=YOUR_KEY&dl_target_url={encoded_url}"
                else:
                    partner_url = "https://aliexpress.ru"
                
                return {
                    'url': partner_url,
                    'cashback_percent': 'до 10%',
                    'network': 'epn'
                }
            
            elif marketplace == 'ozon':
                return {
                    'url': original_url or 'https://ozon.ru',
                    'cashback_percent': 'до 7%',
                    'network': 'epn'
                }
            
            elif marketplace == 'wildberries':
                return {
                    'url': original_url or 'https://wildberries.ru',
                    'cashback_percent': 'до 5%',
                    'network': 'epn'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации EPN ссылки: {e}", exc_info=True)
            return None
    
    def _get_marketplace(self, shop: str) -> Optional[str]:
        """
        Определяет маркетплейс по названию магазина.
        """
        shop_lower = shop.lower()
        for key, value in self.marketplace_map.items():
            if key in shop_lower:
                return value
        return None