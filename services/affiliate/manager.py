"""
Менеджер партнерских программ.

Управляет работой с Admitad партнерской программой для генерации кэшбэк-ссылок.
"""

import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from .admitad import AdmitadService

logger = logging.getLogger(__name__)


class AffiliateManager:
    """
    Менеджер для работы с партнерскими программами.
    
    Управляет генерацией кэшбэк-ссылок через Admitad для всех поддерживаемых магазинов.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация с настройками из config.
        
        Args:
            config: Словарь с настройками для Admitad сервиса
        """
        self.config = config
        
        # Инициализируем единственный сервис - Admitad
        self.admitad = AdmitadService({
            'auth_header': config.get('ADMITAD_AUTH_HEADER'),
            'website_id': config.get('ADMITAD_WEBSITE_ID')
        })
        
        # Список поддерживаемых магазинов через Admitad
        # Все эти магазины работают через единственную партнерскую программу
        self.supported_shops = [
            'wildberries',
            'ozon',
            'lamoda',
            'mvideo',
            'yandex_market',
            'sber'
        ]
    
    def detect_shop_from_url(self, url: str) -> Optional[str]:
        """
        Определяет магазин по URL.
        
        Парсит доменное имя из URL и возвращает идентификатор магазина.
        Этот идентификатор затем используется для проверки поддержки
        и получения процента кэшбэка.
        
        Args:
            url: URL товара или магазина
            
        Returns:
            str: Идентификатор магазина или None если не распознан
        """
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc or parsed.path
            
            # Убираем www. если есть
            domain = domain.replace('www.', '')
            
            # Определяем магазин по домену
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
                logger.warning(f"Неизвестный домен: {domain}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка парсинга URL: {e}")
            return None
    
    async def generate_affiliate_link(
        self,
        original_url: str,
        user_id: int,
        product_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Генерирует партнерскую ссылку с кэшбэком через Admitad.
        
        Args:
            original_url: Оригинальная ссылка на товар
            user_id: ID пользователя
            product_info: Информация о товаре
            
        Returns:
            Dict с полями:
                - affiliate_url: Партнерская ссылка
                - network: Всегда 'admitad'
                - cashback_percent: Процент кэшбэка
                - shop: Название магазина
                - error: Сообщение об ошибке (если не удалось)
        """
        # Определяем какой магазин из ссылки
        shop = self.detect_shop_from_url(original_url)
        
        # Проверяем что магазин поддерживается
        if not shop:
            return {
                'error': 'Магазин не поддерживается',
                'original_url': original_url
            }
        
        # Проверяем что магазин есть в списке поддерживаемых Admitad
        if shop not in self.supported_shops:
            return {
                'error': f'Магазин {shop} не поддерживается через Admitad',
                'original_url': original_url,
                'shop': shop
            }
        
        # Проверяем что Admitad настроен (есть API ключи)
        if not self.admitad.is_configured():
            logger.error("Admitad не настроен - отсутствуют ADMITAD_AUTH_HEADER или ADMITAD_WEBSITE_ID")
            return {
                'error': 'Кэшбэк-сервис временно недоступен',
                'original_url': original_url,
                'shop': shop
            }
        
        # Пытаемся создать партнерскую ссылку через Admitad
        try:
            affiliate_url = await self.admitad.generate_affiliate_link(
                original_url, user_id, product_info
            )
            
            # Если ссылка успешно создана
            if affiliate_url:
                # Получаем процент кэшбэка для этого магазина
                cashback_percent = await self.admitad.get_cashback_percent(
                    shop, 
                    product_info.get('category', '') if product_info else ''
                )
                
                # Возвращаем успешный результат
                return {
                    'affiliate_url': affiliate_url,
                    'network': 'admitad',
                    'cashback_percent': cashback_percent,
                    'shop': shop
                }
            else:
                # Admitad вернул None - значит не смог создать ссылку
                logger.warning(f"Admitad не смог создать ссылку для {shop}")
                return {
                    'error': 'Не удалось создать кэшбэк-ссылку для этого магазина',
                    'original_url': original_url,
                    'shop': shop
                }
                
        except Exception as e:
            # Произошла непредвиденная ошибка при обращении к Admitad
            logger.error(f"Ошибка при генерации ссылки через Admitad: {e}", exc_info=True)
            return {
                'error': 'Кэшбэк-сервис временно недоступен',
                'original_url': original_url,
                'shop': shop
            }
    
    async def check_all_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Проверяет статус всех pending заказов через Admitad.
        
        Этот метод используется фоновой задачей (например, Celery worker),
        которая периодически запускается и проверяет все заказы в статусе
        'pending' - то есть те, которые ожидают подтверждения от магазина.
        
        Когда магазин подтверждает заказ, статус меняется на 'confirmed',
        и пользователю начисляется кэшбэк на баланс.
        
        Returns:
            List словарей с обновленными статусами. Каждый словарь содержит:
                - link_id: ID партнерской ссылки
                - user_id: ID пользователя Telegram
                - status: Новый статус ('confirmed' или 'rejected')
                - amount: Сумма заказа в рублях
                - cashback_amount: Сумма кэшбэка к начислению
        """
        from database.connection import async_session_maker
        from database.models import AffiliateLink
        from sqlalchemy import select
        
        updated_orders = []
        
        # Проверяем что Admitad настроен перед началом работы
        if not self.admitad.is_configured():
            logger.error(
                "Admitad не настроен - невозможно проверить заказы. "
                "Проверьте наличие ADMITAD_AUTH_HEADER и ADMITAD_WEBSITE_ID в .env"
            )
            return []
        
        try:
            async with async_session_maker() as session:
                # Загружаем все партнерские ссылки со статусом pending из базы данных
                # pending означает что пользователь перешел по ссылке, возможно купил товар,
                # но магазин еще не подтвердил заказ
                result = await session.execute(
                    select(AffiliateLink).where(
                        AffiliateLink.conversion_status == 'pending'
                    )
                )
                pending_links = result.scalars().all()
                
                logger.info(f"Начинаем проверку статуса {len(pending_links)} pending ссылок через Admitad")
                
                # Проходим по каждой ссылке и проверяем её статус
                for link in pending_links:
                    try:
                        # Запрашиваем у Admitad актуальный статус этого заказа
                        status_data = await self.admitad.check_order_status(link.link_id)
                        
                        # Если статус изменился (больше не pending), добавляем в список обновлений
                        if status_data.get('status') != 'pending':
                            updated_orders.append({
                                'link_id': link.link_id,
                                'user_id': link.user_id,
                                'status': status_data.get('status'),
                                'amount': status_data.get('amount', 0),
                                'cashback_amount': status_data.get('cashback_amount', 0)
                            })
                            
                            logger.info(
                                f"Статус ссылки {link.link_id} изменился: "
                                f"pending → {status_data.get('status')}"
                            )
                    
                    except Exception as link_error:
                        # Если произошла ошибка при проверке конкретной ссылки,
                        # логируем её и продолжаем проверять остальные ссылки
                        # Это важно - одна сломанная ссылка не должна блокировать проверку всех остальных
                        logger.error(
                            f"Ошибка при проверке ссылки {link.link_id}: {link_error}",
                            exc_info=True
                        )
                        continue
                
                logger.info(f"Проверка завершена. Обновлено статусов: {len(updated_orders)}")
                return updated_orders
                
        except Exception as e:
            # Критическая ошибка на уровне всей операции (например, проблема с БД)
            logger.error(f"Критическая ошибка при проверке заказов: {e}", exc_info=True)
            return []
