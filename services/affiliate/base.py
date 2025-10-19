"""
Базовый класс для всех партнерских сервисов.

Определяет единый интерфейс для работы с разными партнерскими программами.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AffiliateServiceBase(ABC):
    """
    Абстрактный базовый класс для партнерских сервисов.
    
    Все партнерские программы (Admitad, Backit, Yandex Market) должны
    наследовать этот класс и реализовать его методы.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация сервиса с конфигурацией.
        
        Args:
            config: Словарь с API ключами и настройками
        """
        self.config = config
        self.network_name = "base"
    
    @abstractmethod
    async def generate_affiliate_link(
        self, 
        original_url: str, 
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует партнерскую ссылку с кэшбэком.
        
        Args:
            original_url: Оригинальная ссылка на товар
            user_id: ID пользователя Telegram
            product_info: Дополнительная информация о товаре
            
        Returns:
            str: Партнерская ссылка или None при ошибке
        """
        pass
    
    @abstractmethod
    async def check_order_status(
        self, 
        link_id: int,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверяет статус заказа в партнерской программе.
        
        Args:
            link_id: ID партнерской ссылки в БД
            order_id: ID заказа в магазине (если известен)
            
        Returns:
            Dict с полями:
                - status: pending/confirmed/rejected
                - amount: сумма заказа
                - cashback_amount: сумма кэшбэка
                - details: дополнительная информация
        """
        pass
    
    @abstractmethod
    async def get_cashback_percent(self, shop: str, category: str) -> int:
        """
        Получает процент кэшбэка для магазина и категории.
        
        Args:
            shop: Название магазина (wildberries, ozon, etc.)
            category: Категория товара
            
        Returns:
            int: Процент кэшбэка (например, 5 для 5%)
        """
        pass
    
    def is_configured(self) -> bool:
        """
        Проверяет настроен ли сервис (есть ли API ключи).
        
        Returns:
            bool: True если сервис настроен
        """
        return bool(self.config)
    
    async def validate_url(self, url: str, shop: str) -> bool:
        """
        Проверяет что URL принадлежит поддерживаемому магазину.
        
        Args:
            url: URL для проверки
            shop: Название магазина
            
        Returns:
            bool: True если URL валиден
        """
        # Базовая проверка - наследники могут переопределить
        if not url or not url.startswith('http'):
            return False
        
        shop_domains = {
            'wildberries': 'wildberries.ru',
            'ozon': 'ozon.ru',
            'lamoda': 'lamoda.ru',
            'mvideo': 'mvideo.ru',
            'yandex_market': 'market.yandex.ru',
            'sber': 'sbermarket.ru'
        }
        
        domain = shop_domains.get(shop, '')
        return domain in url if domain else True