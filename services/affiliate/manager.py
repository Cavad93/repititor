"""
Менеджер партнерских программ.

Управляет выбором подходящей партнерской программы для магазина.
"""

import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from .admitad import AdmitadService
from .backit import BackitService
from .yandex_market import YandexMarketService

logger = logging.getLogger(__name__)


class AffiliateManager:
    """
    Менеджер для работы с партнерскими программами.
    
    Выбирает оптимальную партнерскую программу для магазина
    и предоставляет fallback механизмы.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация с настройками из config.
        
        Args:
            config: Словарь с настройками для всех сервисов
        """
        self.config = config
        
        # Инициализируем все сервисы
        self.admitad = AdmitadService({
            'auth_header': config.get('ADMITAD_AUTH_HEADER'),
            'website_id': config.get('ADMITAD_WEBSITE_ID')
        })
        
        self.backit = BackitService({
            'api_key': config.get('BACKIT_API_KEY'),
            'user_id': config.get('BACKIT_USER_ID')
        })
        
        self.yandex_market = YandexMarketService({
            'campaign_id': config.get('YANDEX_MARKET_CAMPAIGN_ID'),
            'api_key': config.get('YANDEX_MARKET_API_KEY')
        })
        
        # Приоритеты партнерских программ для магазинов
        self.shop_priorities = {
            'wildberries': [self.admitad, self.backit],
            'ozon': [self.admitad, self.backit],
            'lamoda': [self.admitad],
            'mvideo': [self.admitad],
            'yandex_market': [self.yandex_market, self.admitad],
            'sber': [self.admitad],
            'aliexpress': [self.backit]
        }
    
    def detect_shop_from_url(self, url: str) -> Optional[str]:
        """
        Определяет магазин по URL.
        
        Args:
            url: URL товара
            
        Returns:
            str: Название магазина или None
        """
        try:
            domain = urlparse(url).netloc.lower()
            
            if 'wildberries.ru' in domain:
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
            elif 'aliexpress' in domain:
                return 'aliexpress'
            else:
                logger.warning(f"Неизвестный магазин: {domain}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка парсинга URL: {e}")
            return None
    
    async def generate_affiliate_link(
        self,
        original_url: str,
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Генерирует партнерскую ссылку с кэшбэком.
        
        Автоматически выбирает подходящую партнерскую программу
        с fallback на резервные варианты.
        
        Args:
            original_url: Оригинальная ссылка на товар
            user_id: ID пользователя
            product_info: Информация о товаре
            
        Returns:
            Dict с полями:
                - affiliate_url: Партнерская ссылка
                - network: Используемая партнерская программа
                - cashback_percent: Процент кэшбэка
                - error: Сообщение об ошибке (если не удалось)
        """
        # Определяем магазин
        shop = self.detect_shop_from_url(original_url)
        if not shop:
            return {
                'error': 'Магазин не поддерживается',
                'original_url': original_url
            }
        
        # Получаем список приоритетных сервисов
        services = self.shop_priorities.get(shop, [self.admitad])
        
        # Пробуем сервисы по порядку приоритета
        for service in services:
            if not service.is_configured():
                logger.info(f"Сервис {service.network_name} не настроен, пропускаем")
                continue
            
            try:
                affiliate_url = await service.generate_affiliate_link(
                    original_url, user_id, product_info
                )
                
                if affiliate_url:
                    cashback_percent = await service.get_cashback_percent(shop, 
                        product_info.get('category', '') if product_info else '')
                    
                    return {
                        'affiliate_url': affiliate_url,
                        'network': service.network_name,
                        'cashback_percent': cashback_percent,
                        'shop': shop
                    }
                    
            except Exception as e:
                logger.error(f"Ошибка в {service.network_name}: {e}")
                continue
        
        # Если все сервисы failed - возвращаем оригинальную ссылку
        logger.warning(f"Не удалось создать партнерскую ссылку для {shop}")
        return {
            'error': 'Кэшбэк-сервис временно недоступен',
            'original_url': original_url,
            'shop': shop
        }
    
    async def check_all_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Проверяет статус всех pending заказов во всех сервисах.
        
        Используется фоновой задачей для обновления статусов.
        
        Returns:
            List словарей с обновленными статусами
        """
        from database.connection import async_session_maker
        from database.models import AffiliateLink
        from sqlalchemy import select
        
        updated_orders = []
        
        try:
            async with async_session_maker() as session:
                # Загружаем все ссылки со статусом pending
                result = await session.execute(
                    select(AffiliateLink).where(
                        AffiliateLink.conversion_status == 'pending'
                    )
                )
                pending_links = result.scalars().all()
                
                logger.info(f"Проверка {len(pending_links)} pending ссылок")
                
                for link in pending_links:
                    # Выбираем сервис на основе network
                    if link.affiliate_network == 'admitad':
                        service = self.admitad
                    elif link.affiliate_network == 'backit':
                        service = self.backit
                    elif link.affiliate_network == 'yandex_market':
                        service = self.yandex_market
                    else:
                        logger.warning(f"Неизвестная сеть: {link.affiliate_network}")
                        continue
                    
                    if not service.is_configured():
                        continue
                    
                    # Проверяем статус
                    status_data = await service.check_order_status(link.link_id)
                    
                    if status_data.get('status') != 'pending':
                        updated_orders.append({
                            'link_id': link.link_id,
                            'user_id': link.user_id,
                            'status': status_data.get('status'),
                            'amount': status_data.get('amount', 0),
                            'cashback_amount': status_data.get('cashback_amount', 0)
                        })
                
                logger.info(f"Обновлено {len(updated_orders)} заказов")
                return updated_orders
                
        except Exception as e:
            logger.error(f"Ошибка проверки заказов: {e}", exc_info=True)
            return []
