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
    
    ОБНОВЛЕНО: Использует адаптивные веса из UserPreference.
    """
    
    # Базовые веса для различных параметров
    CATEGORY_BASE_WEIGHT = 50
    SHOP_BASE_WEIGHT = 30
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
        
        ОБНОВЛЕНО: Применяет адаптивные веса из category_weights и shop_weights.
        
        Формула оценки:
        - Совпадение категории: 50 баллов * adaptive_weight
        - Совпадение магазина: 30 баллов * adaptive_weight
        - Соответствие ценовому диапазону: 20 баллов
        - Бонус за популярность: до 10 баллов (views / 100)
        
        Args:
            user_prefs: Объект предпочтений пользователя
            item: Словарь с данными о предложении
            popularity_views: Количество просмотров предложения
        
        Returns:
            int: Оценка релевантности (0-110+ баллов)
        """
        score = 0.0
        
        # 1. Проверка категории с адаптивным весом
        item_category = item.get('category', '').lower()
        if user_prefs.categories and item_category in user_prefs.categories:
            # Получаем адаптивный вес (по умолчанию 1.0)
            category_weight = user_prefs.category_weights.get(item_category, 1.0) if user_prefs.category_weights else 1.0
            category_score = cls.CATEGORY_BASE_WEIGHT * category_weight
            score += category_score
            logger.debug(f"Категория '{item_category}' совпала: +{category_score:.1f} баллов (вес: {category_weight:.2f})")
        
        # 2. Проверка магазина с адаптивным весом
        item_shop = item.get('shop', '').lower()
        if user_prefs.favorite_shops and item_shop in user_prefs.favorite_shops:
            # Получаем адаптивный вес (по умолчанию 1.0)
            shop_weight = user_prefs.shop_weights.get(item_shop, 1.0) if user_prefs.shop_weights else 1.0
            shop_score = cls.SHOP_BASE_WEIGHT * shop_weight
            score += shop_score
            logger.debug(f"Магазин '{item_shop}' совпал: +{shop_score:.1f} баллов (вес: {shop_weight:.2f})")
        
        # 3. Проверка ценового диапазона (без изменений)
        item_price = item.get('price', 0)
        if cls._is_price_in_range(item_price, user_prefs):
            score += cls.PRICE_WEIGHT
            logger.debug(f"Цена в диапазоне: +{cls.PRICE_WEIGHT} баллов")
        
        # 4. Бонус за популярность (без изменений)
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
        """
        if not user_prefs.price_range_min and not user_prefs.price_range_max:
            return True
        
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
        """
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
        """
        if score >= cls.HIGH_RELEVANCE_THRESHOLD:
            return 'high'
        elif score >= cls.MEDIUM_RELEVANCE_THRESHOLD:
            return 'medium'
        else:
            return 'low'


    @classmethod
    def filter_by_relevance_optimized(
        cls,
        user_prefs: UserPreference,
        items: List[Dict],
        min_score: int = MEDIUM_RELEVANCE_THRESHOLD,
        max_results: int = 100
    ) -> List[Dict]:
        """
        ОПТИМИЗИРОВАННАЯ версия фильтрации для больших датасетов.
        
        Оптимизации:
        1. Предварительная фильтрация по категориям/магазинам перед расчетом оценок
        2. Ограничение количества результатов (top-k)
        3. Ранний выход при достижении лимита
        
        Args:
            user_prefs: Объект предпочтений пользователя
            items: Список предложений
            min_score: Минимальная оценка для включения
            max_results: Максимальное количество результатов (для производительности)
        
        Returns:
            List[Dict]: Топ-N отфильтрованных и отсортированных предложений
        """
        import time
        start_time = time.time()
        
        # Шаг 1: Быстрая предварительная фильтрация
        user_categories = set(user_prefs.categories or [])
        user_shops = set(user_prefs.favorite_shops or [])
        
        # Фильтруем только товары из интересующих категорий/магазинов
        pre_filtered = []
        for item in items:
            item_cat = item.get('category', '').lower()
            item_shop = item.get('shop', '').lower()
            
            # Быстрая проверка без расчета оценки
            if item_cat in user_categories or item_shop in user_shops:
                pre_filtered.append(item)
        
        logger.info(f"Предфильтрация: {len(pre_filtered)} из {len(items)} товаров")
        
        # Шаг 2: Расчет оценок только для предфильтрованных товаров
        scored_items = []
        for item in pre_filtered:
            score = cls.calculate_relevance_score(
                user_prefs,
                item,
                popularity_views=item.get('views', 0)
            )
            
            if score >= min_score:
                item['relevance_score'] = score
                scored_items.append(item)
                
                # Ранний выход если достигли лимита * 2 (для запаса)
                if len(scored_items) >= max_results * 2:
                    break
        
        # Шаг 3: Сортировка и ограничение результатов
        scored_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        result = scored_items[:max_results]
        
        elapsed = (time.time() - start_time) * 1000  # в миллисекундах
        logger.info(
            f"Фильтрация завершена за {elapsed:.1f}ms: "
            f"{len(result)} топовых результатов из {len(items)} предложений "
            f"(порог: {min_score} баллов)"
        )
        
        return result



class AdaptiveLearning:
    """
    Механизм адаптивного обучения на основе поведения пользователя.
    
    ОБНОВЛЕНО: Теперь реально изменяет веса категорий и магазинов.
    """
    
    # Коэффициенты изменения весов
    NEGATIVE_FEEDBACK_DECAY = 0.1  # 10% снижение веса при негативной реакции
    POSITIVE_FEEDBACK_BOOST = 0.15  # 15% повышение веса при позитивной реакции
    
    # Границы весов
    MIN_WEIGHT = 0.5  # Минимальный вес (не опускаемся ниже)
    MAX_WEIGHT = 2.0  # Максимальный вес (не поднимаемся выше)
    
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
        
        ОБНОВЛЕНО: Применяет коэффициенты к весам категорий и магазинов.
        
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
                
                # Инициализируем веса если они пустые
                if not prefs.category_weights:
                    prefs.category_weights = {}
                if not prefs.shop_weights:
                    prefs.shop_weights = {}
                
                # Обновляем веса на основе действия
                if action_type in ['hide', 'not_interested']:
                    # НЕГАТИВНАЯ обратная связь - СНИЖАЕМ вес
                    logger.info(
                        f"Пользователь {user_id} скрыл предложение: категория={item_category}, магазин={item_shop}"
                    )
                    
                    # Снижаем вес категории
                    if item_category:
                        current_weight = prefs.category_weights.get(item_category, 1.0)
                        new_weight = max(current_weight - cls.NEGATIVE_FEEDBACK_DECAY, cls.MIN_WEIGHT)
                        prefs.category_weights[item_category] = new_weight
                        logger.info(f"  Вес категории '{item_category}': {current_weight:.2f} → {new_weight:.2f}")
                    
                    # Снижаем вес магазина
                    if item_shop:
                        current_weight = prefs.shop_weights.get(item_shop, 1.0)
                        new_weight = max(current_weight - cls.NEGATIVE_FEEDBACK_DECAY, cls.MIN_WEIGHT)
                        prefs.shop_weights[item_shop] = new_weight
                        logger.info(f"  Вес магазина '{item_shop}': {current_weight:.2f} → {new_weight:.2f}")
                
                elif action_type in ['click', 'track']:
                    # ПОЗИТИВНАЯ обратная связь - ПОВЫШАЕМ вес
                    logger.info(
                        f"Пользователь {user_id} заинтересовался: категория={item_category}, магазин={item_shop}"
                    )
                    
                    # Повышаем вес категории
                    if item_category:
                        current_weight = prefs.category_weights.get(item_category, 1.0)
                        new_weight = min(current_weight + cls.POSITIVE_FEEDBACK_BOOST, cls.MAX_WEIGHT)
                        prefs.category_weights[item_category] = new_weight
                        logger.info(f"  Вес категории '{item_category}': {current_weight:.2f} → {new_weight:.2f}")
                    
                    # Повышаем вес магазина
                    if item_shop:
                        current_weight = prefs.shop_weights.get(item_shop, 1.0)
                        new_weight = min(current_weight + cls.POSITIVE_FEEDBACK_BOOST, cls.MAX_WEIGHT)
                        prefs.shop_weights[item_shop] = new_weight
                        logger.info(f"  Вес магазина '{item_shop}': {current_weight:.2f} → {new_weight:.2f}")
                    
                    # Если категория не в предпочтениях - предлагаем добавить
                    if prefs.categories and item_category not in prefs.categories:
                        logger.info(
                            f"Категория '{item_category}' может быть интересна пользователю {user_id} (не в настройках)"
                        )
                
                await session.commit()
                logger.info(f"Веса обновлены для пользователя {user_id}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке взаимодействия: {e}", exc_info=True)
                await session.rollback()
