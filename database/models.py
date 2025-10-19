from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, Integer, ForeignKey, VARCHAR, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import secrets
import string

from database.connection import Base


def generate_referral_code(length: int = 8) -> str:
    """
    Генерирует уникальный реферальный код для пользователя.
    
    Код состоит из букв и цифр для удобства копирования и передачи.
    Длина по умолчанию 8 символов обеспечивает достаточную уникальность.
    
    Args:
        length: Длина генерируемого кода
        
    Returns:
        str: Случайный реферальный код
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class User(Base):
    """
    Модель пользователя Telegram бота.
    
    Хранит основную информацию о пользователе, полученную из Telegram,
    а также данные для работы реферальной системы и отслеживания активности.
    
    Attributes:
        user_id: Уникальный Telegram ID пользователя (первичный ключ)
        username: Username в Telegram (может быть None если не установлен)
        first_name: Имя пользователя из Telegram
        last_name: Фамилия пользователя из Telegram (опционально)
        phone: Номер телефона если пользователь поделился (опционально)
        registration_date: Timestamp регистрации пользователя в боте
        last_activity: Timestamp последнего взаимодействия с ботом
        is_active: Флаг активности аккаунта (для блокировки пользователей)
        referral_code: Уникальный код для приглашения друзей
        referred_by: ID пользователя который пригласил этого пользователя
    """
    __tablename__ = 'users'
    
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
    
    Управляет типом подписки, сроками действия и параметрами оплаты.
    Поддерживает пробный период и автоматическое продление.
    
    Attributes:
        subscription_id: Уникальный ID подписки
        user_id: ID пользователя (связь с таблицей users)
        subscription_type: Тип подписки (trial, paid, expired)
        start_date: Дата начала текущего периода подписки
        end_date: Дата окончания подписки
        is_trial_used: Флаг использования пробного периода
        payment_method: Способ оплаты (card, yookassa, etc)
        auto_renewal: Включено ли автопродление подписки
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
        
        Returns:
            bool: True если подписка активна (дата окончания в будущем)
        """
        return self.end_date > datetime.now() if self.end_date else False


class UserPreference(Base):
    """
    Модель настроек персонализации пользователя.
    
    Хранит предпочтения по категориям товаров, магазинам, ценовому диапазону
    и параметры уведомлений для персонализированного опыта.
    
    Attributes:
        preference_id: Уникальный ID записи настроек
        user_id: ID пользователя (связь с таблицей users)
        categories: JSON массив выбранных категорий товаров
        favorite_shops: JSON массив избранных магазинов
        price_range_min: Минимальная цена в фильтре товаров
        price_range_max: Максимальная цена в фильтре товаров
        notification_frequency: Частота уведомлений (instant, daily, weekly)
        notification_time: Предпочитаемое время для получения уведомлений
    """
    __tablename__ = 'user_preferences'
    
    preference_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, unique=True, index=True, comment="Reference to user")
    categories = Column(JSONB, default=list, nullable=False, comment="Array of selected product categories")
    favorite_shops = Column(JSONB, default=list, nullable=False, comment="Array of favorite shops")
    price_range_min = Column(Integer, nullable=True, comment="Minimum price filter")
    price_range_max = Column(Integer, nullable=True, comment="Maximum price filter")
    notification_frequency = Column(VARCHAR(20), default='instant', nullable=False, comment="Notification frequency")
    notification_time = Column(Time, nullable=True, comment="Preferred notification time")
    
    def __repr__(self):
        return f"<UserPreference(user={self.user_id}, freq={self.notification_frequency})>"