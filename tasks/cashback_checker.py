"""
Фоновая задача для проверки статусов заказов.

Запускается периодически для обновления статусов pending транзакций.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from database.connection import async_session_maker
from database.models import AffiliateLink, CashbackTransaction
from services.affiliate.manager import AffiliateManager
from utils.balance import BalanceManager
from config.settings import settings
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


async def check_pending_orders():
    """
    Проверяет статус всех pending заказов во всех партнерских программах.
    
    Эта функция должна запускаться периодически (например, каждый час).
    """
    logger.info("=" * 60)
    logger.info("ЗАПУСК ПРОВЕРКИ PENDING ЗАКАЗОВ")
    logger.info("=" * 60)
    
    try:
        # Инициализируем менеджер
        affiliate_manager = AffiliateManager({
            'ADMITAD_AUTH_HEADER': settings.ADMITAD_AUTH_HEADER,
            'ADMITAD_WEBSITE_ID': settings.ADMITAD_WEBSITE_ID,
            'BACKIT_API_KEY': settings.BACKIT_API_KEY,
            'BACKIT_USER_ID': settings.BACKIT_USER_ID,
            'YANDEX_MARKET_CAMPAIGN_ID': settings.YANDEX_MARKET_CAMPAIGN_ID,
            'YANDEX_MARKET_API_KEY': settings.YANDEX_MARKET_API_KEY
        })
        
        # Проверяем все pending заказы
        updated_orders = await affiliate_manager.check_all_pending_orders()
        
        logger.info(f"Найдено {len(updated_orders)} обновленных заказов")
        
        # Обрабатываем обновленные заказы
        async with async_session_maker() as session:
            for order in updated_orders:
                try:
                    link_id = order['link_id']
                    user_id = order['user_id']
                    status = order['status']
                    cashback_amount = order['cashback_amount']
                    
                    # Обновляем статус ссылки
                    result = await session.execute(
                        select(AffiliateLink).where(AffiliateLink.link_id == link_id)
                    )
                    link = result.scalar_one_or_none()
                    
                    if link:
                        link.conversion_status = status
                    
                    # Если статус confirmed - начисляем кэшбэк
                    if status == 'confirmed' and cashback_amount > 0:
                        # Проверяем нет ли уже транзакции
                        tx_result = await session.execute(
                            select(CashbackTransaction).where(
                                and_(
                                    CashbackTransaction.link_id == link_id,
                                    CashbackTransaction.status == 'confirmed'
                                )
                            )
                        )
                        existing_tx = tx_result.scalar_one_or_none()
                        
                        if not existing_tx:
                            # Создаем транзакцию
                            transaction = CashbackTransaction(
                                user_id=user_id,
                                link_id=link_id,
                                order_id=order.get('order_id'),
                                order_amount=order.get('amount', 0),
                                cashback_percent=5,  # TODO: Получать из партнерской программы
                                cashback_amount=cashback_amount,
                                status='confirmed',
                                confirmed_at=datetime.now()
                            )
                            session.add(transaction)
                            await session.flush()
                            
                            # Подтверждаем баланс
                            await BalanceManager.confirm_pending_balance(
                                session,
                                user_id,
                                cashback_amount,
                                f"Кэшбэк подтвержден (заказ #{order.get('order_id', 'N/A')})",
                                transaction.transaction_id
                            )
                            
                            logger.info(
                                f"✓ Подтвержден кэшбэк {cashback_amount}₽ "
                                f"для пользователя {user_id}"
                            )
                            
                            # TODO: Отправить уведомление пользователю
                    
                    # Если статус rejected - убираем из pending
                    elif status == 'rejected':
                        # Создаем транзакцию с rejected
                        transaction = CashbackTransaction(
                            user_id=user_id,
                            link_id=link_id,
                            cashback_amount=0,
                            cashback_percent=0,
                            status='rejected'
                        )
                        session.add(transaction)
                        
                        logger.info(f"✗ Заказ отклонен для пользователя {user_id}")
                    
                    await session.commit()
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки заказа {order}: {e}", exc_info=True)
                    await session.rollback()
                    continue
        
        logger.info("=" * 60)
        logger.info("ПРОВЕРКА ЗАВЕРШЕНА")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Критическая ошибка проверки заказов: {e}", exc_info=True)


async def run_periodic_checker(interval_hours: int = 1):
    """
    Запускает периодическую проверку заказов.
    
    Args:
        interval_hours: Интервал проверки в часах
    """
    logger.info(f"Запущен периодический чекер заказов (каждые {interval_hours} час)")
    
    while True:
        try:
            await check_pending_orders()
        except Exception as e:
            logger.error(f"Ошибка в цикле чекера: {e}", exc_info=True)
        
        # Ждем следующего цикла
        await asyncio.sleep(interval_hours * 3600)


if __name__ == "__main__":
    # Для тестирования
    asyncio.run(check_pending_orders())
