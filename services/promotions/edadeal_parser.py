# services/promotions/edadeal_parser.py

"""
Полный парсер акций из Едадила с поддержкой реального API.
"""

import logging
import json
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from .base_parser import BasePromotionParser

logger = logging.getLogger(__name__)


class EdadealParser(BasePromotionParser):
    """
    Парсер акций из Едадила через публичное API.
    
    API эндпоинты:
    - https://api.edadeal.ru/web/search/offers
    - https://squark.edadeal.ru/web/search/offers (альтернативный)
    """
    
    def __init__(self):
        super().__init__('edadeal', 'https://edadeal.ru')
        # Используем основной API эндпоинт
        self.api_base = 'https://api.edadeal.ru/web'
        self.alt_api_base = 'https://squark.edadeal.ru/web'
        
        # Маппинг категорий
        self.category_map = {
            'food': 'Продукты',
            'pharmacy': 'Аптека',
            'beauty': 'Косметика',
            'children': 'Детские товары',
            'pets': 'Зоотовары',
            'clothes': 'Одежда',
            'electronics': 'Электроника',
            'sport': 'Спорт',
            'home': 'Дом',
            'auto': 'Авто',
        }
        
        # Маппинг городов
        self.city_map = {
            'москва': 'moskva',
            'санкт-петербург': 'sankt-peterburg',
            'екатеринбург': 'ekaterinburg',
            'новосибирск': 'novosibirsk',
            'казань': 'kazan',
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
            categories: Список категорий ['food', 'pharmacy', ...]
            retailers: Список магазинов ['5ka', 'perekrestok', ...]
            max_pages: Максимум страниц для парсинга
            
        Returns:
            List[Dict]: Список акций
        """
        logger.info(f"Запуск парсинга Едадила: город={city}, категории={categories}")
        
        all_promotions = []
        
        # Если категории не указаны - берем основные
        if not categories:
            categories = ['food', 'pharmacy', 'beauty']
        
        for category in categories:
            logger.info(f"  Категория: {category}")
            
            # Парсим страницы для категории
            for page in range(1, max_pages + 1):
                try:
                    promotions = await self._parse_page(
                        city=city,
                        category=category,
                        page=page,
                        retailer=retailers[0] if retailers else None
                    )
                    
                    if not promotions:
                        logger.info(f"    Страница {page}: акций нет, останавливаем")
                        break
                    
                    logger.info(f"    Страница {page}: {len(promotions)} акций")
                    all_promotions.extend(promotions)
                    
                    # Задержка между запросами
                    await asyncio.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Ошибка парсинга страницы {page} категории {category}: {e}")
                    continue
        
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
        """
        # Параметры запроса
        params = {
            'count': 30,
            'locality': city,
            'page': page,
        }
        
        if category:
            params['segment'] = category
        
        if retailer:
            params['retailer'] = retailer
        
        # Формируем URL
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        
        # Пробуем основной API
        url = f"{self.api_base}/search/offers?{query_string}"
        result = await self.fetch(url)
        
        # Если основной не работает - пробуем альтернативный
        if result['error'] or result['status'] != 200:
            logger.warning(f"Основной API недоступен, пробуем альтернативный")
            url = f"{self.alt_api_base}/search/offers?{query_string}"
            result = await self.fetch(url)
        
        if result['error'] or result['status'] != 200:
            logger.error(f"Ошибка запроса: status={result['status']}, error={result['error']}")
            return []
        
        # Парсим ответ
        try:
            return self._parse_response(result['content'])
        except Exception as e:
            logger.error(f"Ошибка обработки ответа: {e}", exc_info=True)
            return []
    
    def _parse_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Парсит ответ API (JSON или protobuf).
        """
        promotions = []
        
        try:
            # Пробуем JSON
            data = json.loads(content)
            
            # Извлекаем оферы
            offers = data.get('offers', [])
            if not offers and 'data' in data:
                offers = data['data'].get('offers', [])
            if not offers and 'results' in data:
                offers = data['results']
            
            # Парсим каждый оффер
            for offer in offers:
                promo = self._parse_offer(offer)
                if promo:
                    promotions.append(promo)
            
            return promotions
            
        except json.JSONDecodeError:
            # Если не JSON - может быть protobuf или base64
            logger.warning("Ответ не в JSON, пытаемся декодировать base64")
            try:
                decoded = base64.b64decode(content)
                # Здесь нужна protobuf библиотека для полного парсинга
                # Пока возвращаем пустой список
                logger.warning("Protobuf декодирование пока не реализовано")
                return []
            except Exception as e:
                logger.error(f"Ошибка декодирования: {e}")
                return []
    
    def _parse_offer(self, offer: Dict) -> Optional[Dict[str, Any]]:
        """
        Парсит один оффер в стандартный формат.
        """
        try:
            # Название
            title = (
                offer.get('name') or 
                offer.get('title') or 
                offer.get('offer_title') or 
                ''
            )
            if not title or len(title) < 3:
                return None
            
            # Магазин
            retailer = offer.get('retailer', {})
            if isinstance(retailer, dict):
                shop_name = retailer.get('name', '')
                shop_id = retailer.get('id', '')
            else:
                shop_name = str(retailer)
                shop_id = ''
            
            if not shop_name:
                shop_name = offer.get('retailer_name', 'Неизвестно')
            
            shop_normalized = self.normalize_shop_name(shop_name)
            
            # Категория
            category = offer.get('category', {})
            if isinstance(category, dict):
                category_name = category.get('name', 'products')
            else:
                category_name = str(category) if category else 'products'
            
            category_normalized = self.normalize_category(category_name)
            
            # Цены
            price_info = offer.get('price', {})
            price_old = None
            price_new = None
            
            if isinstance(price_info, dict):
                price_old = price_info.get('old') or price_info.get('price_old')
                price_new = price_info.get('new') or price_info.get('price_new') or price_info.get('current')
            
            # Конвертируем в копейки если нужно
            if price_old and price_old < 1000000:
                price_old = int(price_old * 100)
            if price_new and price_new < 1000000:
                price_new = int(price_new * 100)
            
            # Скидка
            discount_percent = offer.get('discount') or offer.get('discount_percent')
            if not discount_percent and price_old and price_new and price_old > price_new:
                discount_percent = int(((price_old - price_new) / price_old) * 100)
            
            discount_amount = None
            if price_old and price_new:
                discount_amount = price_old - price_new
            
            # Даты
            start_date = self._parse_date(
                offer.get('start_date') or 
                offer.get('date_from') or 
                offer.get('published_at')
            )
            end_date = self._parse_date(
                offer.get('end_date') or 
                offer.get('date_to') or 
                offer.get('expired_at')
            )
            
            # URL
            offer_url = (
                offer.get('url') or 
                offer.get('link') or 
                offer.get('offer_url')
            )
            if offer_url and not offer_url.startswith('http'):
                offer_url = f"https://edadeal.ru{offer_url}"
            
            # Изображение
            image_url = (
                offer.get('image') or 
                offer.get('image_url') or 
                offer.get('img')
            )
            if image_url and not image_url.startswith('http'):
                image_url = f"https:{image_url}" if image_url.startswith('//') else f"https://edadeal.ru{image_url}"
            
            # Промокод
            promo_code = offer.get('promo_code') or offer.get('coupon_code') or offer.get('code')
            
            # Описание
            description = offer.get('description', '') or offer.get('text', '')
            
            # Внешний ID
            external_id = str(offer.get('id', '')) or str(offer.get('offer_id', ''))
            
            return {
                'external_id': external_id,
                'source': 'edadeal',
                'title': title[:500],  # Ограничиваем длину
                'description': description[:2000] if description else '',
                'shop': shop_normalized,
                'shop_original': shop_name,
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
                'quality_score': 75,  # Едадил - проверенный источник
                'extra_data': offer,  # Сохраняем оригинал
            }
            
        except Exception as e:
            logger.error(f"Ошибка парсинга оффера: {e}", exc_info=True)
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Парсит дату из разных форматов.
        """
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%d.%m.%Y',
            '%d.%m.%Y %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue
        
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None
