from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, Integer, ForeignKey, VARCHAR, Time
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import secrets
import string

from database.connection import Base


def generate_referral_code(length: int = 8) -> str:
    """
    Генерирует уникальный реферальный код для пользователя.
    
    НЕ ИЗМЕНИЛОСЬ: Генерация случайных кодов не зависит от типа базы данных.
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class User(Base):
    """
    Модель пользователя Telegram бота.
    
    ИЗМЕНЕНО: Минимальные изменения для совместимости с SQLite.
    Основная структура таблицы осталась прежней - те же колонки с теми же типами.
    
    Главное отличие: SQLite имеет более простую систему типов чем PostgreSQL,
    но SQLAlchemy автоматически преобразует типы в подходящие для SQLite.
    """
    __tablename__ = 'users'
    
    # Все типы колонок остались прежними
    # SQLAlchemy автоматически конвертирует их в совместимые с SQLite типы:
    # BigInteger -> INTEGER в SQLite
    # VARCHAR -> TEXT в SQLite
    # Boolean -> INTEGER (0 или 1) в SQLite
    # TIMESTAMP -> TEXT (ISO формат) в SQLite
    
    user_id = Column(BigInteger, primary_key=True, index=True, comment="Telegram User ID")
    username = Column(VARCHAR(255), nullable=True, comment="Telegram username")
    first_name = Column(VARCHAR(255), nullable=False, comment="First name from Telegram")
    last_name = Column(VARCHAR(255), nullable=True, comment="Last name from Telegram")
    phone = Column(VARCHAR(20), nullable=True, comment="Phone number if shared")
    registration_date = Column(TIMESTAMP, default=func.now(), nullable=False, comment="Registration timestamp")
    last_activity = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False, comment="Last interaction timestamp")
    is_active = Column(Boolean, default=True, nullable=False, comment="Account active status")
    referral_code = Column(VARCHAR(10), unique=True, nullable=False, default=generate_referral_code, comment="Unique referral code")
    referred_by = Column(BigInteger, ForeignKey('users.user_id'), nullable=True, comment="Referrer user ID")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, name={self.first_name})>"


class Subscription(Base):
    """
    Модель подписки пользователя.
    
    НЕ ИЗМЕНИЛОСЬ: Структура таблицы абсолютно идентична версии для PostgreSQL.
    SQLite прекрасно справляется с хранением подписок и всех их параметров.
    """
    __tablename__ = 'subscriptions'
    
    subscription_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True, comment="Reference to user")
    subscription_type = Column(VARCHAR(50), nullable=False, default='trial', comment="Type: trial, paid, expired")
    start_date = Column(TIMESTAMP, default=func.now(), nullable=False, comment="Subscription start date")
    end_date = Column(TIMESTAMP, nullable=False, comment="Subscription end date")
    is_trial_used = Column(Boolean, default=False, nullable=False, comment="Trial period used flag")
    payment_method = Column(VARCHAR(50), nullable=True, comment="Payment method used")
    auto_renewal = Column(Boolean, default=False, nullable=False, comment="Auto-renewal enabled")
    
    def __repr__(self):
        return f"<Subscription(id={self.subscription_id}, user={self.user_id}, type={self.subscription_type})>"
    
    @property
    def is_active(self) -> bool:
        """
        Проверяет активна ли подписка на текущий момент.
        
        НЕ ИЗМЕНИЛОСЬ: Бизнес-логика не зависит от типа базы данных.
        """
        return self.end_date > datetime.now() if self.end_date else False


class UserPreference(Base):
    """
    Модель настроек персонализации пользователя.
    
    ОБНОВЛЕНО: Добавлены поля для адаптивных весов категорий и магазинов.
    """
    __tablename__ = 'user_preferences'
    
    preference_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, unique=True, index=True, comment="Reference to user")
    
    # JSON колонки для списков
    categories = Column(JSON, default=list, nullable=False, comment="Array of selected product categories")
    favorite_shops = Column(JSON, default=list, nullable=False, comment="Array of favorite shops")
    
    # НОВОЕ: Адаптивные веса для категорий и магазинов
    # Формат JSON: {"electronics": 1.2, "clothing": 0.8, ...}
    # Базовый вес = 1.0, увеличивается/уменьшается при взаимодействиях
    category_weights = Column(JSON, default=dict, nullable=False, comment="Adaptive weights for categories")
    shop_weights = Column(JSON, default=dict, nullable=False, comment="Adaptive weights for shops")
    
    price_range_min = Column(Integer, nullable=True, comment="Minimum price filter")
    price_range_max = Column(Integer, nullable=True, comment="Maximum price filter")
    notification_frequency = Column(VARCHAR(20), default='instant', nullable=False, comment="Notification frequency")
    notification_time = Column(Time, nullable=True, comment="Preferred notification time")
    
    def __repr__(self):
        return f"<UserPreference(user={self.user_id}, freq={self.notification_frequency})>"

class UserInteraction(Base):
    """
    Модель для отслеживания взаимодействий пользователя с предложениями.
    
    Эта таблица логирует все действия пользователя для адаптивного обучения
    и улучшения персонализации со временем.
    
    Типы действий:
    - view: просмотр предложения
    - click: клик по ссылке
    - track: добавление в отслеживаемые
    - hide: скрытие предложения
    - not_interested: пометка как неинтересное
    """
    __tablename__ = 'user_interactions'
    
    interaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True, comment="Reference to user")
    action_type = Column(VARCHAR(50), nullable=False, comment="Type of action: view, click, track, hide, not_interested")
    item_id = Column(VARCHAR(255), nullable=True, comment="ID of the item (deal, product, promo)")
    item_category = Column(VARCHAR(100), nullable=True, comment="Category of the item")
    item_shop = Column(VARCHAR(100), nullable=True, comment="Shop/marketplace of the item")
    item_price = Column(Integer, nullable=True, comment="Price of the item")
    timestamp = Column(TIMESTAMP, default=func.now(), nullable=False, comment="When the action occurred")
    extra_data = Column(JSON, default=dict, nullable=True, comment="Additional metadata about the interaction")
    
    def __repr__(self):
        return f"<UserInteraction(user={self.user_id}, action={self.action_type}, category={self.item_category})>"


class AffiliateLink(Base):
    """
    Модель для хранения партнерских ссылок с кэшбэком.
    
    Каждая ссылка привязана к пользователю и партнерской программе.
    Отслеживаем клики и конверсии для начисления кэшбэка.
    """
    __tablename__ = 'affiliate_links'
    
    link_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True, comment="User who got the link")
    
    original_url = Column(String(2048), nullable=False, comment="Original product URL")
    affiliate_url = Column(String(2048), nullable=False, comment="Affiliate link with cashback")
    
    affiliate_network = Column(VARCHAR(50), nullable=False, comment="Partner network: admitad, backit, yandex_market")
    
    # JSON с информацией о товаре
    product_info = Column(JSON, default=dict, nullable=False, comment="Product details: title, price, category, shop")
    
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, comment="Link creation time")
    
    clicks_count = Column(Integer, default=0, nullable=False, comment="Number of clicks")
    last_click_at = Column(TIMESTAMP, nullable=True, comment="Last click timestamp")
    
    # Статус конверсии: pending, approved, rejected
    conversion_status = Column(VARCHAR(20), default='pending', nullable=False, comment="Conversion status")
    
    def __repr__(self):
        return f"<AffiliateLink(id={self.link_id}, user={self.user_id}, network={self.affiliate_network})>"


class CashbackTransaction(Base):
    """
    Модель для транзакций кэшбэка.
    
    Фиксирует все начисления кэшбэка по партнерским ссылкам.
    Отслеживаем статус от pending до paid.
    """
    __tablename__ = 'cashback_transactions'
    
    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True, comment="User who earned cashback")
    link_id = Column(BigInteger, ForeignKey('affiliate_links.link_id'), nullable=True, comment="Related affiliate link")
    
    order_id = Column(VARCHAR(255), nullable=True, comment="Order ID from shop")
    order_amount = Column(Integer, nullable=True, comment="Order amount in rubles")
    
    cashback_percent = Column(Integer, nullable=False, comment="Cashback percentage")
    cashback_amount = Column(Integer, nullable=False, comment="Cashback amount in rubles")
    
    # Статус: pending (ожидает), confirmed (подтвержден), paid (выплачен), rejected (отклонен)
    status = Column(VARCHAR(20), default='pending', nullable=False, index=True, comment="Transaction status")
    
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, comment="Transaction creation")
    confirmed_at = Column(TIMESTAMP, nullable=True, comment="When confirmed by partner")
    paid_at = Column(TIMESTAMP, nullable=True, comment="When paid to user")
    
    # Дополнительная информация
    extra_data = Column(JSON, default=dict, nullable=True, comment="Additional metadata")
    
    def __repr__(self):
        return f"<CashbackTransaction(id={self.transaction_id}, user={self.user_id}, amount={self.cashback_amount}, status={self.status})>"


class UserBalance(Base):
    """
    Модель баланса кэшбэка пользователя.
    
    Один пользователь = одна запись с балансом.
    """
    __tablename__ = 'user_balances'
    
    balance_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, unique=True, index=True, comment="User who owns the balance")
    
    # Текущий доступный баланс (можно вывести)
    current_balance = Column(Integer, default=0, nullable=False, comment="Available balance in rubles")
    
    # Ожидающий подтверждения кэшбэк
    pending_balance = Column(Integer, default=0, nullable=False, comment="Pending cashback in rubles")
    
    # Статистика
    total_earned = Column(Integer, default=0, nullable=False, comment="Total earned ever")
    total_withdrawn = Column(Integer, default=0, nullable=False, comment="Total withdrawn")
    
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False, comment="Last update")
    
    def __repr__(self):
        return f"<UserBalance(user={self.user_id}, balance={self.current_balance}₽, pending={self.pending_balance}₽)>"


class BalanceOperation(Base):
    """
    Модель операций с балансом.
    
    Логирует все изменения баланса для прозрачности и отладки.
    """
    __tablename__ = 'balance_operations'
    
    operation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True, comment="User")
    
    # Тип операции: credit (начисление), debit (списание), withdrawal (вывод)
    operation_type = Column(VARCHAR(20), nullable=False, comment="Operation type")
    
    amount = Column(Integer, nullable=False, comment="Amount in rubles")
    
    balance_before = Column(Integer, nullable=False, comment="Balance before operation")
    balance_after = Column(Integer, nullable=False, comment="Balance after operation")
    
    description = Column(String(512), nullable=True, comment="Operation description")
    
    # Ссылка на транзакцию если операция связана с кэшбэком
    transaction_id = Column(Integer, ForeignKey('cashback_transactions.transaction_id'), nullable=True, comment="Related transaction")
    
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, comment="Operation time")
    
    def __repr__(self):
        return f"<BalanceOperation(id={self.operation_id}, user={self.user_id}, type={self.operation_type}, amount={self.amount})>"


# database/models.py
# В конец файла добавить:

class Promotion(Base):
    """
    Модель для хранения акций и промокодов из агрегаторов.
    
    Агрегируем акции из Едадила и других источников.
    Используется для персонализированной выдачи пользователям.
    """
    __tablename__ = 'promotions'
    
    promotion_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Идентификаторы
    external_id = Column(VARCHAR(255), nullable=False, index=True, comment="ID from source (Edadeal, etc)")
    source = Column(VARCHAR(50), nullable=False, default='edadeal', comment="Source: edadeal, manual, etc")
    
    # Основная информация
    title = Column(String(512), nullable=False, comment="Promotion title")
    description = Column(String(2048), nullable=True, comment="Full description")
    shop = Column(VARCHAR(100), nullable=False, index=True, comment="Shop name: pyaterochka, magnit, etc")
    category = Column(VARCHAR(100), nullable=False, index=True, comment="Category: products, pharmacy, etc")
    
    # Цены и скидки
    price_old = Column(Integer, nullable=True, comment="Old price in kopecks")
    price_new = Column(Integer, nullable=True, comment="New price in kopecks")
    discount_percent = Column(Integer, nullable=True, comment="Discount percentage")
    discount_amount = Column(Integer, nullable=True, comment="Discount amount in kopecks")
    
    # Промокод
    promo_code = Column(VARCHAR(100), nullable=True, comment="Promo code if available")
    
    # Ссылки
    url = Column(String(2048), nullable=True, comment="Link to promotion")
    image_url = Column(String(2048), nullable=True, comment="Image URL")
    
    # Даты действия
    start_date = Column(TIMESTAMP, nullable=True, comment="Promotion start date")
    end_date = Column(TIMESTAMP, nullable=True, index=True, comment="Promotion end date")
    
    # Метаданные
    views_count = Column(Integer, default=0, nullable=False, comment="Number of views")
    clicks_count = Column(Integer, default=0, nullable=False, comment="Number of clicks")
    quality_score = Column(Integer, default=50, nullable=False, comment="Quality score 0-100")
    
    # Статус
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="Is active")
    
    # Временные метки
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, comment="Created timestamp")
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False, comment="Last update")
    
    # JSON с дополнительными данными
    extra_data = Column(JSON, default=dict, nullable=True, comment="Additional data from source")
    
    def __repr__(self):
        return f"<Promotion(id={self.promotion_id}, shop={self.shop}, title={self.title[:30]})>"
    
    def is_expired(self) -> bool:
        """Проверяет истекла ли акция."""
        if not self.end_date:
            return False
        return self.end_date < datetime.now()
