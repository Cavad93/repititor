# services/promotions/base_parser.py

"""
Базовый класс для парсеров акций.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import aiohttp
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class BasePromotionParser(ABC):
    """
    Базовый класс для всех парсеров акций.
    
    Обеспечивает:
    - Проверку robots.txt
    - Задержки между запросами
    - Правильный User-Agent
    - Обработку ошибок
    """
    
    def __init__(self, source_name: str, base_url: str):
        """
        Args:
            source_name: Имя источника (edadeal, pyaterochka, etc)
            base_url: Базовый URL сайта
        """
        self.source_name = source_name
        self.base_url = base_url
        self.user_agent = (
            f"RepititorBot/1.0 (+https://t.me/your_bot; support@example.com)"
        )
        self.delay = 3.0  # Секунды между запросами
        self.robots_parser = None
    
    async def check_robots_txt(self, url: str) -> bool:
        """
        Проверяет разрешен ли доступ к URL согласно robots.txt.
        
        Args:
            url: URL для проверки
            
        Returns:
            bool: True если доступ разрешен
        """
        if not self.robots_parser:
            await self._load_robots_txt()
        
        if not self.robots_parser:
            # Если не удалось загрузить robots.txt - разрешаем
            return True
        
        try:
            parsed = urlparse(url)
            path = parsed.path + ('?' + parsed.query if parsed.query else '')
            return self.robots_parser.can_fetch(self.user_agent, path)
        except Exception as e:
            logger.error(f"Ошибка проверки robots.txt: {e}")
            return True
    
    async def _load_robots_txt(self):
        """Загружает и парсит robots.txt сайта."""
        try:
            robots_url = f"{self.base_url}/robots.txt"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    robots_url,
                    headers={'User-Agent': self.user_agent},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.robots_parser = RobotFileParser()
                        self.robots_parser.parse(content.splitlines())
                        logger.info(f"✓ robots.txt загружен для {self.source_name}")
                    else:
                        logger.warning(
                            f"robots.txt не найден для {self.source_name} "
                            f"(status {response.status})"
                        )
        except Exception as e:
            logger.warning(f"Не удалось загрузить robots.txt: {e}")
    
    async def fetch(self, url: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос с соблюдением правил.
        
        Args:
            url: URL для запроса
            method: HTTP метод
            **kwargs: Дополнительные параметры для aiohttp
            
        Returns:
            Dict с ключами: status, content, error
        """
        # Проверяем robots.txt
        if not await self.check_robots_txt(url):
            logger.warning(f"Доступ к {url} запрещен robots.txt")
            return {'status': 403, 'error': 'Blocked by robots.txt'}
        
        # Добавляем задержку
        import asyncio
        await asyncio.sleep(self.delay)
        
        try:
            headers = kwargs.pop('headers', {})
            headers['User-Agent'] = self.user_agent
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                    **kwargs
                ) as response:
                    content = await response.read()
                    
                    return {
                        'status': response.status,
                        'content': content,
                        'headers': dict(response.headers),
                        'error': None
                    }
        
        except Exception as e:
            logger.error(f"Ошибка запроса {url}: {e}")
            return {'status': 0, 'error': str(e)}
    
    @abstractmethod
    async def parse(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Парсит акции из источника.
        
        Должен быть реализован в подклассе.
        
        Returns:
            List[Dict]: Список акций в стандартизированном формате
        """
        pass
    
    def normalize_shop_name(self, shop: str) -> str:
        """
        Нормализует название магазина к единому формату.
        
        Args:
            shop: Исходное название
            
        Returns:
            str: Нормализованное название
        """
        shop = shop.lower().strip()
        
        # Маппинг вариантов написания к стандартным
        shop_mapping = {
            'пятёрочка': 'pyaterochka',
            'пятерочка': 'pyaterochka',
            '5': 'pyaterochka',
            'магнит': 'magnit',
            'перекрёсток': 'perekrestok',
            'перекресток': 'perekrestok',
            'вкусвилл': 'vkusvill',
            'лента': 'lenta',
            'ашан': 'auchan',
            'дикси': 'dixy',
            'магнит косметик': 'magnit_kosmetik',
            'золотое яблоко': 'zolotoe_yabloko',
            'ригла': 'rigla',
            'детский мир': 'detskiy_mir',
            'wildberries': 'wildberries',
            'ozon': 'ozon',
            'lamoda': 'lamoda',
            'mvideo': 'mvideo',
            'мвидео': 'mvideo',
        }
        
        return shop_mapping.get(shop, shop.replace(' ', '_'))
    
    def normalize_category(self, category: str) -> str:
        """
        Нормализует категорию к стандартному формату.
        
        Args:
            category: Исходная категория
            
        Returns:
            str: Нормализованная категория
        """
        category = category.lower().strip()
        
        category_mapping = {
            'продукты': 'products',
            'еда': 'products',
            'food': 'products',
            'аптеки': 'pharmacy',
            'pharmacy': 'pharmacy',
            'косметика': 'cosmetics',
            'beauty': 'cosmetics',
            'одежда': 'clothing',
            'clothes': 'clothing',
            'электроника': 'electronics',
            'electronics': 'electronics',
            'детские товары': 'children',
            'kids': 'children',
            'зоотовары': 'pets',
            'pets': 'pets',
            'спорт': 'sports',
            'sports': 'sports',
        }
        
        return category_mapping.get(category, category)