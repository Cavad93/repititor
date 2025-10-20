# services/promotions/edadeal_parser.py

"""
Парсер акций из Едадила.

Едадил использует API с данными в формате Protobuf/JSON.
Парсим публичные эндпоинты с соблюдением правил.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64

from .base_parser import BasePromotionParser

logger = logging.getLogger(__name__)


class EdadealParser(BasePromotionParser):
    """
    Парсер акций из Едадила.
    
    API эндпоинты:
    - /web/search/offers - поиск акций
    - /web/retailers - список магазинов
    """
    
    def __init__(self):
        super().__init__('edadeal', 'https://edadeal.ru')
        self.api_base = 'https://api.edadeal.ru/web'
        
        # Маппинг категорий Едадила к нашим
        self.category_map = {
            'food': 'products',
            'pharmacy': 'pharmacy',
            'beauty': 'cosmetics',
            'children': 'children',
            'pets': 'pets',
            'clothes': 'clothing',
            'electronics': 'electronics',
            'sport': 'sports',
            'home': 'home',
            'auto': 'auto',
        }
    
    async def parse(
        self,
        city: str = 'moskva',
        categories: Optional[List[str]] = None,
        retailers: Optional[List[str]] = None,
        max_pages: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Парсит акции из Едадила.
        
        Args:
            city: Город (moskva, sankt-peterburg, etc)
            categories: Список категорий для фильтрации
            retailers: Список магазинов для фильтрации
            max_pages: Максимум страниц для парсинга
            
        Returns:
            List[Dict]: Список акций
        """
        logger.info(f"Начинаю парсинг Едадила для города {city}")
        
        all_promotions = []
        
        # Если не указаны категории - берем все основные
        if not categories:
            categories = ['food', 'pharmacy', 'beauty', 'children']
        
        for category in categories:
            logger.info(f"  Парсинг категории: {category}")
            
            for page in range(1, max_pages + 1):
                promotions = await self._parse_page(
                    city=city,
                    category=category,
                    page=page,
                    retailer=retailers[0] if retailers else None
                )
                
                if not promotions:
                    logger.info(f"    Страница {page}: акций не найдено, останавливаем")
                    break
                
                logger.info(f"    Страница {page}: найдено {len(promotions)} акций")
                all_promotions.extend(promotions)
        
        logger.info(f"✓ Парсинг завершен: {len(all_promotions)} акций")
        return all_promotions
    
    async def _parse_page(
        self,
        city: str,
        category: str,
        page: int,
        retailer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Парсит одну страницу акций.
        
        Args:
            city: Город
            category: Категория
            page: Номер страницы
            retailer: Фильтр по магазину
            
        Returns:
            List[Dict]: Акции со страницы
        """
        # Формируем URL
        params = {
            'count': 30,
            'locality': city,
            'page': page,
        }
        
        if category:
            params['segment'] = category
        
        if retailer:
            params['retailer'] = retailer
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{self.api_base}/search/offers?{query_string}"
        
        # Выполняем запрос
        result = await self.fetch(url)
        
        if result['error'] or result['status'] != 200:
            logger.error(
                f"Ошибка запроса страницы {page}: "
                f"status={result['status']}, error={result['error']}"
            )
            return []
        
        # Парсим ответ
        try:
            # Едадил может возвращать разные форматы
            content = result['content']
            
            # Пробуем JSON
            try:
                data = json.loads(content)
                return self._parse_json_response(data)
            except json.JSONDecodeError:
                # Возможно это Protobuf или другой формат
                logger.warning("Ответ не в JSON формате, пропускаем")
                return []
        
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа: {e}", exc_info=True)
            return []
    
    def _parse_json_response(self, data: Dict) -> List[Dict[str, Any]]:
        """
        Парсит JSON ответ от Едадила.
        
        Args:
            data: JSON данные
            
        Returns:
            List[Dict]: Список акций
        """
        promotions = []
        
        # Структура может быть разной, адаптируем
        offers = data.get('offers', [])
        if not offers and 'data' in data:
            offers = data['data'].get('offers', [])
        
        for offer in offers:
            try:
                promo = self._parse_offer(offer)
                if promo:
                    promotions.append(promo)
            except Exception as e:
                logger.error(f"Ошибка парсинга оффера: {e}")
                continue
        
        return promotions
    
    def _parse_offer(self, offer: Dict) -> Optional[Dict[str, Any]]:
        """
        Парсит один оффер из Едадила.
        
        Args:
            offer: Данные оффера
            
        Returns:
            Dict: Стандартизированные данные акции
        """
        # Извлекаем основные поля
        title = offer.get('name') or offer.get('title') or ''
        if not title:
            return None
        
        # Магазин
        retailer = offer.get('retailer', {})
        shop_name = retailer.get('name', '') if isinstance(retailer, dict) else str(retailer)
        shop_normalized = self.normalize_shop_name(shop_name)
        
        # Категория
        category = offer.get('category', {})
        category_name = category.get('name', 'products') if isinstance(category, dict) else str(category)
        category_normalized = self.normalize_category(category_name)
        
        # Цены
        price_info = offer.get('price', {})
        price_old = price_info.get('old')
        price_new = price_info.get('new') or price_info.get('current')
        
        # Конвертируем в копейки если в рублях
        if price_old and price_old < 1000000:  # Скорее всего в рублях
            price_old = int(price_old * 100)
        if price_new and price_new < 1000000:
            price_new = int(price_new * 100)
        
        # Скидка
        discount_percent = offer.get('discount_percent')
        if not discount_percent and price_old and price_new:
            discount_percent = int(((price_old - price_new) / price_old) * 100)
        
        discount_amount = None
        if price_old and price_new:
            discount_amount = price_old - price_new
        
        # Даты
        start_date = self._parse_date(offer.get('start_date') or offer.get('date_from'))
        end_date = self._parse_date(offer.get('end_date') or offer.get('date_to'))
        
        # URL и изображение
        offer_url = offer.get('url') or offer.get('link')
        image_url = offer.get('image') or offer.get('image_url')
        
        # Промокод
        promo_code = offer.get('promo_code') or offer.get('coupon_code')
        
        # Описание
        description = offer.get('description', '')
        
        return {
            'external_id': str(offer.get('id', '')),
            'source': 'edadeal',
            'title': title,
            'description': description,
            'shop': shop_normalized,
            'category': category_normalized,
            'price_old': price_old,
            'price_new': price_new,
            'discount_percent': discount_percent,
            'discount_amount': discount_amount,
            'promo_code': promo_code,
            'url': offer_url,
            'image_url': image_url,
            'start_date': start_date,
            'end_date': end_date,
            'quality_score': 70,  # Едадил - надежный источник
            'extra_data': offer,  # Сохраняем оригинальные данные
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Парсит дату из разных форматов.
        
        Args:
            date_str: Строка с датой
            
        Returns:
            datetime или None
        """
        if not date_str:
            return None
        
        # Пробуем разные форматы
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue
        
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None


# Экспортируем для удобства
__all__ = ['EdadealParser']