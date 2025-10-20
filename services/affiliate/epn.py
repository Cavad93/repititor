"""
Сервис для работы с EPN партнерской программой.

EPN - крупнейшая российская CPA-сеть с офферами Wildberries, Ozon, Lamoda и др.
Использует OAuth 2.0 для авторизации и систему Deeplink для генерации ссылок.
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
import time
from urllib.parse import quote

from .base import AffiliateServiceBase

logger = logging.getLogger(__name__)


class EPNService(AffiliateServiceBase):
    """
    Сервис для генерации партнерских ссылок через EPN.
    
    Использует систему Deeplink для создания партнерских ссылок.
    Для каждого магазина нужен свой Deeplink hash.
    
    ВАЖНО: Для работы нужны:
    - EPN_DEEPLINK_HASHES (словарь магазинов и их deeplink hash)
    - Опционально: EPN_CLIENT_ID и EPN_CLIENT_SECRET для Cabinet API
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.network_name = "epn"
        
        # Словарь соответствия магазинов и их deeplink hash
        # Формат: {'wildberries': 'abc123def456', 'ozon': 'xyz789'}
        self.deeplink_hashes = config.get('deeplink_hashes', {})
        
        # OAuth параметры (опционально, для Cabinet API)
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.access_token = None
        
        # URL эндпоинтов EPN
        self.redirect_base = "http://alipromo.com/redirect/cpa/o"
        self.oauth_url = "https://epn.bz/oauth/token"
    
    def is_configured(self) -> bool:
        """
        Проверяет что сервис настроен правильно.
        
        Для работы необходим хотя бы один deeplink hash.
        """
        if not self.deeplink_hashes or len(self.deeplink_hashes) == 0:
            logger.warning("EPN_DEEPLINK_HASHES пустой - добавьте хотя бы один магазин")
            return False
        
        return True
    
    async def generate_affiliate_link(
        self, 
        original_url: str, 
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует партнерскую ссылку через EPN Deeplink.
        
        Процесс работы:
        1. Определяем магазин из URL
        2. Получаем deeplink hash для этого магазина
        3. Формируем партнерскую ссылку с subid для трекинга
        4. Кодируем оригинальный URL в параметр to
        
        Args:
            original_url: Ссылка на товар
            user_id: Telegram ID пользователя
            product_info: Информация о товаре (не используется)
            
        Returns:
            str: Партнерская ссылка с трекингом или None при ошибке
        """
        if not self.is_configured():
            logger.error("EPN не настроен - проверьте .env файл")
            return None
        
        try:
            # Определяем магазин из URL
            shop = self._detect_shop(original_url)
            if not shop:
                logger.warning(f"Не удалось определить магазин из URL: {original_url}")
                return None
            
            # Получаем deeplink hash для этого магазина
            deeplink_hash = self.deeplink_hashes.get(shop)
            if not deeplink_hash:
                logger.warning(f"Deeplink hash не найден для магазина {shop}")
                return None
            
            # Формируем subid для отслеживания
            # Формат: tg_<user_id>_<timestamp>
            subid = f"tg_{user_id}_{int(time.time())}"
            
            logger.info(f"Создание EPN deeplink для пользователя {user_id}")
            logger.debug(f"Original URL: {original_url}")
            logger.debug(f"Deeplink hash: {deeplink_hash}")
            logger.debug(f"SubID: {subid}")
            
            # Формируем финальную партнерскую ссылку
            # Формат: http://alipromo.com/redirect/cpa/o/{hash}?to={encoded_url}&sub1={subid}
            encoded_url = quote(original_url, safe='')
            
            affiliate_url = (
                f"{self.redirect_base}/{deeplink_hash}"
                f"?to={encoded_url}"
                f"&sub1={subid}"
            )
            
            logger.info(f"✓ EPN deeplink создан для user {user_id}")
            logger.debug(f"Affiliate link: {affiliate_url[:80]}...")
            
            return affiliate_url
        
        except Exception as e:
            logger.error(f"Ошибка при генерации EPN ссылки: {e}", exc_info=True)
            return None
    
    async def get_access_token(self) -> Optional[str]:
        """
        Получает access token через OAuth 2.0.
        
        Используется для работы с Cabinet API (статистика, креативы).
        Не требуется для базовой генерации deeplink.
        
        Returns:
            str: Access token или None при ошибке
        """
        if not self.client_id or not self.client_secret:
            logger.warning("EPN OAuth не настроен - client_id/client_secret отсутствуют")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
                
                async with session.post(self.oauth_url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.access_token = result.get('access_token')
                        logger.info("✓ EPN access token получен")
                        return self.access_token
                    else:
                        logger.error(f"Ошибка получения EPN токена: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Ошибка OAuth EPN: {e}", exc_info=True)
            return None
    
    async def check_order_status(
        self, 
        link_id: int,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверяет статус заказа в EPN.
        
        Требует Cabinet API с access token.
        
        Args:
            link_id: ID партнерской ссылки в БД
            order_id: ID заказа (не используется)
            
        Returns:
            Dict со статусом заказа
        """
        try:
            logger.info(f"Проверка статуса EPN для link_id={link_id}")
            
            # Заглушка - требуется реализация через Cabinet API
            return {
                'status': 'pending',
                'amount': 0,
                'cashback_amount': 0,
                'details': 'Проверка статуса EPN в разработке'
            }
        
        except Exception as e:
            logger.error(f"Ошибка проверки статуса EPN: {e}", exc_info=True)
            return {
                'status': 'error',
                'amount': 0,
                'cashback_amount': 0,
                'details': str(e)
            }
    
    async def get_cashback_percent(self, shop: str, category: str = '') -> int:
        """
        Получает процент кэшбэка для магазина.
        
        В EPN проценты зависят от конкретного оффера.
        Используем примерные значения для популярных магазинов.
        
        Args:
            shop: Название магазина
            category: Категория товара
            
        Returns:
            int: Процент кэшбэка
        """
        # Типичные проценты кэшбэка в EPN
        cashback_rates = {
            'wildberries': 5,
            'ozon': 4,
            'lamoda': 6,
            'mvideo': 3,
            'detmir': 5,
            'sber': 3,
            'yandex_market': 2
        }
        
        base_rate = cashback_rates.get(shop, 3)
        
        if category in ['electronics', 'clothing']:
            base_rate += 1
        
        return base_rate
    
    def _detect_shop(self, url: str) -> Optional[str]:
        """
        Определяет магазин по URL.
        
        Args:
            url: URL товара
            
        Returns:
            str: Идентификатор магазина или None
        """
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc or parsed.path
            domain = domain.replace('www.', '')
            
            if 'wildberries.ru' in domain or 'wb.ru' in domain:
                return 'wildberries'
            elif 'ozon.ru' in domain:
                return 'ozon'
            elif 'lamoda.ru' in domain:
                return 'lamoda'
            elif 'mvideo.ru' in domain:
                return 'mvideo'
            elif 'market.yandex.ru' in domain:
                return 'yandex_market'
            elif 'sbermarket.ru' in domain or 'sbermegamarket.ru' in domain:
                return 'sber'
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка парсинга URL: {e}")
            return None