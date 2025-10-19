"""
Модуль персонализации рекомендаций.

Содержит алгоритмы оценки релевантности предложений
на основе пользовательских предпочтений и поведения.
"""

import logging
from typing import List, Dict, Optional
from database.models import UserPreference

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    """
    Движок персонализации для оценки релевантности предложений.
    
    Использует весовую модель для расчета оценки каждого предложения
    на основе предпочтений пользователя.
    """
    
    # Веса для различных параметров
    CATEGORY_WEIGHT = 50
    SHOP_WEIGHT = 30
    PRICE_WEIGHT = 20
    POPULARITY_WEIGHT_MAX = 10
    
    # Пороги релевантности
    HIGH_RELEVANCE_THRESHOLD = 70
    MEDIUM_RELEVANCE_THRESHOLD = 40
    
    @classmethod
    def calculate_relevance_score(
        cls,
        user_prefs: UserPreference,
        item: Dict,
        popularity_views: int = 0
    ) -> int:
        """
        Вычисляет оценку релевантности предложения для пользователя.
        
        Формула оценки:
        - Совпадение категории: 50 баллов
        - Совпадение магазина: 30 баллов
        - Соответствие ценовому диапазону: 20 баллов
        - Бонус за популярность: до 10 баллов (views / 100)
        
        Args:
            user_prefs: Объект предпочтений пользователя
            item: Словарь с данными о предложении
                {
                    'category': str,
                    'shop': str,
                    'price': int,
                    'title': str,
                    ...
                }
            popularity_views: Количество просмотров предложения другими пользователями
        
        Returns:
            int: Оценка релевантности (0-110 баллов)
        """
        score = 0
        
        # 1. Проверка категории (50 баллов)
        item_category = item.get('category', '').lower()
        if user_prefs.categories and item_category in user_prefs.categories:
            score += cls.CATEGORY_WEIGHT
            logger.debug(f"Категория совпала: +{cls.CATEGORY_WEIGHT} баллов")
        
        # 2. Проверка магазина (30 баллов)
        item_shop = item.get('shop', '').lower()
        if user_prefs.favorite_shops and item_shop in user_prefs.favorite_shops:
            score += cls.SHOP_WEIGHT
            logger.debug(f"Магазин совпал: +{cls.SHOP_WEIGHT} баллов")
        
        # 3. Проверка ценового диапазона (20 баллов)
        item_price = item.get('price', 0)
        if cls._is_price_in_range(item_price, user_prefs):
            score += cls.PRICE_WEIGHT
            logger.debug(f"Цена в диапазоне: +{cls.PRICE_WEIGHT} баллов")
        
        # 4. Бонус за популярность (до 10 баллов)
        popularity_bonus = min(popularity_views / 100, cls.POPULARITY_WEIGHT_MAX)
        score += popularity_bonus
        logger.debug(f"Бонус популярности: +{popularity_bonus:.1f} баллов")
        
        logger.info(
            f"Оценка релевантности для товара '{item.get('title', 'Unknown')}': {score:.1f} баллов"
        )
        
        return int(score)
    
    @classmethod
    def _is_price_in_range(cls, price: int, user_prefs: UserPreference) -> bool:
        """
        Проверяет попадает ли цена в диапазон предпочтений пользователя.
        
        Args:
            price: Цена товара
            user_prefs: Объект предпочтений пользователя
        
        Returns:
            bool: True если цена подходит
        """
        # Если диапазон не задан - подходит любая цена
        if not user_prefs.price_range_min and not user_prefs.price_range_max:
            return True
        
        # Проверяем попадание в диапазон
        min_price = user_prefs.price_range_min or 0
        max_price = user_prefs.price_range_max or float('inf')
        
        return min_price <= price <= max_price
    
    @classmethod
    def filter_by_relevance(
        cls,
        user_prefs: UserPreference,
        items: List[Dict],
        min_score: int = MEDIUM_RELEVANCE_THRESHOLD
    ) -> List[Dict]:
        """
        Фильтрует список предложений по релевантности.
        
        Args:
            user_prefs: Объект предпочтений пользователя
            items: Список предложений
            min_score: Минимальная оценка для включения в результат
        
        Returns:
            List[Dict]: Отфильтрованный и отсортированный список предложений
        """
        # Вычисляем оценки для каждого предложения
        scored_items = []
        for item in items:
            score = cls.calculate_relevance_score(
                user_prefs,
                item,
                popularity_views=item.get('views', 0)
            )
            
            if score >= min_score:
                item['relevance_score'] = score
                scored_items.append(item)
        
        # Сортируем по убыванию релевантности
        scored_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        logger.info(
            f"Отфильтровано {len(scored_items)} из {len(items)} предложений "
            f"(порог: {min_score} баллов)"
        )
        
        return scored_items
    
    @classmethod
    def categorize_by_relevance(cls, score: int) -> str:
        """
        Определяет категорию релевантности по оценке.
        
        Args:
            score: Оценка релевантности
        
        Returns:
            str: 'high', 'medium' или 'low'
        """
        if score >= cls.HIGH_RELEVANCE_THRESHOLD:
            return 'high'
        elif score >= cls.MEDIUM_RELEVANCE_THRESHOLD:
            return 'medium'
        else:
            return 'low'


class AdaptiveLearning:
    """
    Механизм адаптивного обучения на основе поведения пользователя.
    
    Анализирует взаимодействия пользователя и корректирует
    веса персонализации для улучшения рекомендаций.
    """
    
    # Коэффициенты изменения весов
    NEGATIVE_FEEDBACK_DECAY = 0.1  # 10% снижение веса при негативной реакции
    POSITIVE_FEEDBACK_BOOST = 0.15  # 15% повышение веса при позитивной реакции
    
    @classmethod
    async def process_interaction(
        cls,
        user_id: int,
        action_type: str,
        item_category: str,
        item_shop: str
    ):
        """
        Обрабатывает взаимодействие пользователя и обновляет предпочтения.
        
        Args:
            user_id: ID пользователя
            action_type: Тип действия (view, click, track, hide, not_interested)
            item_category: Категория товара
            item_shop: Магазин
        """
        from database.connection import async_session_maker
        from database.models import UserPreference, UserInteraction
        from sqlalchemy import select
        
        async with async_session_maker() as session:
            try:
                # Логируем взаимодействие
                interaction = UserInteraction(
                    user_id=user_id,
                    action_type=action_type,
                    item_category=item_category,
                    item_shop=item_shop
                )
                session.add(interaction)
                
                # Загружаем предпочтения пользователя
                result = await session.execute(
                    select(UserPreference).where(UserPreference.user_id == user_id)
                )
                prefs = result.scalar_one_or_none()
                
                if not prefs:
                    logger.warning(f"Предпочтения пользователя {user_id} не найдены")
                    await session.commit()
                    return
                
                # Обновляем предпочтения на основе действия
                if action_type in ['hide', 'not_interested']:
                    # Негативная обратная связь - снижаем вес категории
                    logger.info(
                        f"Пользователь {user_id} скрыл предложение из категории {item_category}"
                    )
                    # TODO: Реализовать логику снижения веса
                    # (требует добавления полей для хранения весов в UserPreference)
                
                elif action_type in ['click', 'track']:
                    # Позитивная обратная связь
                    logger.info(
                        f"Пользователь {user_id} заинтересовался категорией {item_category}"
                    )
                    
                    # Если категория не в предпочтениях - предлагаем добавить
                    if prefs.categories and item_category not in prefs.categories:
                        # TODO: Отправить пользователю уведомление с предложением
                        # добавить категорию в настройки
                        logger.info(
                            f"Категория {item_category} может быть интересна пользователю {user_id}"
                        )
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Ошибка при обработке взаимодействия: {e}", exc_info=True)
                await session.rollback()