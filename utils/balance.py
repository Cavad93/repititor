"""
Утилиты для работы с балансом кэшбэка пользователей.

Обеспечивает транзакционную целостность при начислениях и списаниях.
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserBalance, BalanceOperation, CashbackTransaction

logger = logging.getLogger(__name__)


class BalanceManager:
    """
    Менеджер для безопасной работы с балансами пользователей.
    
    Все операции с балансом логируются в balance_operations
    для обеспечения прозрачности и возможности аудита.
    """
    
    @staticmethod
    async def get_or_create_balance(session: AsyncSession, user_id: int) -> UserBalance:
        """
        Получает баланс пользователя или создает новый.
        
        Args:
            session: Асинхронная сессия БД
            user_id: ID пользователя
            
        Returns:
            UserBalance: Объект баланса
        """
        result = await session.execute(
            select(UserBalance).where(UserBalance.user_id == user_id)
        )
        balance = result.scalar_one_or_none()
        
        if not balance:
            balance = UserBalance(
                user_id=user_id,
                current_balance=0,
                pending_balance=0,
                total_earned=0,
                total_withdrawn=0
            )
            session.add(balance)
            await session.flush()
            logger.info(f"Создан новый баланс для пользователя {user_id}")
        
        return balance
    
    @staticmethod
    async def credit_balance(
        session: AsyncSession,
        user_id: int,
        amount: int,
        description: str,
        transaction_id: Optional[int] = None
    ) -> bool:
        """
        Начисляет средства на баланс пользователя.
        
        Args:
            session: Асинхронная сессия БД
            user_id: ID пользователя
            amount: Сумма начисления в рублях
            description: Описание операции
            transaction_id: ID связанной транзакции кэшбэка
            
        Returns:
            bool: True если успешно
        """
        try:
            balance = await BalanceManager.get_or_create_balance(session, user_id)
            
            balance_before = balance.current_balance
            balance.current_balance += amount
            balance.total_earned += amount
            balance.updated_at = datetime.now()
            balance_after = balance.current_balance
            
            # Логируем операцию
            operation = BalanceOperation(
                user_id=user_id,
                operation_type='credit',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=description,
                transaction_id=transaction_id
            )
            session.add(operation)
            
            await session.flush()
            
            logger.info(
                f"Начислено {amount}₽ пользователю {user_id}. "
                f"Баланс: {balance_before}₽ → {balance_after}₽"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка начисления баланса: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def debit_balance(
        session: AsyncSession,
        user_id: int,
        amount: int,
        description: str,
        transaction_id: Optional[int] = None
    ) -> bool:
        """
        Списывает средства с баланса пользователя.
        
        Args:
            session: Асинхронная сессия БД
            user_id: ID пользователя
            amount: Сумма списания в рублях
            description: Описание операции
            transaction_id: ID связанной транзакции
            
        Returns:
            bool: True если успешно, False если недостаточно средств
        """
        try:
            balance = await BalanceManager.get_or_create_balance(session, user_id)
            
            if balance.current_balance < amount:
                logger.warning(
                    f"Недостаточно средств для списания {amount}₽ "
                    f"у пользователя {user_id} (баланс: {balance.current_balance}₽)"
                )
                return False
            
            balance_before = balance.current_balance
            balance.current_balance -= amount
            balance.updated_at = datetime.now()
            balance_after = balance.current_balance
            
            # Логируем операцию
            operation = BalanceOperation(
                user_id=user_id,
                operation_type='debit',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=description,
                transaction_id=transaction_id
            )
            session.add(operation)
            
            await session.flush()
            
            logger.info(
                f"Списано {amount}₽ у пользователя {user_id}. "
                f"Баланс: {balance_before}₽ → {balance_after}₽"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка списания баланса: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def add_pending_balance(
        session: AsyncSession,
        user_id: int,
        amount: int
    ) -> bool:
        """
        Добавляет сумму в pending баланс (ожидает подтверждения).
        
        Args:
            session: Асинхронная сессия БД
            user_id: ID пользователя
            amount: Сумма в рублях
            
        Returns:
            bool: True если успешно
        """
        try:
            balance = await BalanceManager.get_or_create_balance(session, user_id)
            
            balance.pending_balance += amount
            balance.updated_at = datetime.now()
            
            await session.flush()
            
            logger.info(f"Добавлено {amount}₽ в pending баланс пользователя {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления pending баланса: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def confirm_pending_balance(
        session: AsyncSession,
        user_id: int,
        amount: int,
        description: str,
        transaction_id: Optional[int] = None
    ) -> bool:
        """
        Переводит pending баланс в current (подтверждение кэшбэка).
        
        Args:
            session: Асинхронная сессия БД
            user_id: ID пользователя
            amount: Сумма для подтверждения
            description: Описание
            transaction_id: ID транзакции
            
        Returns:
            bool: True если успешно
        """
        try:
            balance = await BalanceManager.get_or_create_balance(session, user_id)
            
            if balance.pending_balance < amount:
                logger.error(
                    f"Недостаточно pending баланса для подтверждения {amount}₽ "
                    f"у пользователя {user_id}"
                )
                return False
            
            balance.pending_balance -= amount
            balance_before = balance.current_balance
            balance.current_balance += amount
            balance.total_earned += amount
            balance.updated_at = datetime.now()
            balance_after = balance.current_balance
            
            # Логируем операцию
            operation = BalanceOperation(
                user_id=user_id,
                operation_type='credit',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=description,
                transaction_id=transaction_id
            )
            session.add(operation)
            
            await session.flush()
            
            logger.info(
                f"Подтвержден кэшбэк {amount}₽ для пользователя {user_id}. "
                f"Баланс: {balance_before}₽ → {balance_after}₽"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подтверждения баланса: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_balance_info(session: AsyncSession, user_id: int) -> dict:
        """
        Получает полную информацию о балансе пользователя.
        
        Returns:
            dict: Словарь с информацией о балансе
        """
        balance = await BalanceManager.get_or_create_balance(session, user_id)
        
        return {
            'current_balance': balance.current_balance,
            'pending_balance': balance.pending_balance,
            'total_earned': balance.total_earned,
            'total_withdrawn': balance.total_withdrawn,
            'updated_at': balance.updated_at
        }