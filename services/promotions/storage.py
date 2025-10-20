# services/promotions/storage.py

"""
Сервис для сохранения акций в БД.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from database.connection import async_session_maker
from database.models import Promotion

logger = logging.getLogger(__name__)


class PromotionStorage:
    """Сервис для работы с акциями в БД."""
    
    @staticmethod
    async def save_promotions(promotions: List[Dict[str, Any]]) -> int:
        """
        Сохраняет список акций в БД.
        
        Использует upsert: обновляет существующие или создает новые.
        
        Args:
            promotions: Список акций для сохранения
            
        Returns:
            int: Количество сохраненных акций
        """
        if not promotions:
            return 0
        
        saved_count = 0
        
        async with async_session_maker() as session:
            for promo_data in promotions:
                try:
                    # Проверяем есть ли уже такая акция
                    result = await session.execute(
                        select(Promotion).where(
                            Promotion.external_id == promo_data['external_id'],
                            Promotion.source == promo_data['source']
                        )
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Обновляем существующую
                        for key, value in promo_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.now()
                    else:
                        # Создаем новую
                        promotion = Promotion(**promo_data)
                        session.add(promotion)
                    
                    saved_count += 1
                
                except Exception as e:
                    logger.error(f"Ошибка сохранения акции: {e}")
                    continue
            
            await session.commit()
        
        logger.info(f"✓ Сохранено/обновлено {saved_count} акций")
        return saved_count
    
    @staticmethod
    async def get_active_promotions(
        shop: str = None,
        category: str = None,
        limit: int = 100
    ) -> List[Promotion]:
        """
        Получает активные акции с фильтрацией.
        
        Args:
            shop: Фильтр по магазину
            category: Фильтр по категории
            limit: Максимум результатов
            
        Returns:
            List[Promotion]: Список акций
        """
        async with async_session_maker() as session:
            query = select(Promotion).where(
                Promotion.is_active == True
            )
            
            # Фильтр по дате окончания
            query = query.where(
                (Promotion.end_date == None) | 
                (Promotion.end_date > datetime.now())
            )
            
            if shop:
                query = query.where(Promotion.shop == shop)
            
            if category:
                query = query.where(Promotion.category == category)
            
            query = query.order_by(Promotion.quality_score.desc())
            query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def increment_views(promotion_id: int):
        """Увеличивает счетчик просмотров."""
        async with async_session_maker() as session:
            await session.execute(
                update(Promotion)
                .where(Promotion.promotion_id == promotion_id)
                .values(views_count=Promotion.views_count + 1)
            )
            await session.commit()
    
    @staticmethod
    async def increment_clicks(promotion_id: int):
        """Увеличивает счетчик кликов."""
        async with async_session_maker() as session:
            await session.execute(
                update(Promotion)
                .where(Promotion.promotion_id == promotion_id)
                .values(clicks_count=Promotion.clicks_count + 1)
            )
            await session.commit()
    
    @staticmethod
    async def deactivate_expired():
        """Деактивирует истекшие акции."""
        async with async_session_maker() as session:
            await session.execute(
                update(Promotion)
                .where(
                    Promotion.is_active == True,
                    Promotion.end_date < datetime.now()
                )
                .values(is_active=False)
            )
            await session.commit()
            logger.info("✓ Истекшие акции деактивированы")
            
    @classmethod
    async def get_stats_by_shop(cls) -> Dict[str, int]:
        """
        Возвращает статистику по магазинам.
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            from database.models import Promotion
            
            result = await session.execute(
                select(Promotion.shop, func.count(Promotion.id))
                .where(Promotion.is_active == True)
                .group_by(Promotion.shop)
            )
            
            return {shop: count for shop, count in result.all()}
