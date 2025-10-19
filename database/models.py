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
    
    ИЗМЕНЕНО: Тип JSON колонок изменен с JSONB на JSON.
    PostgreSQL использует специальный бинарный формат JSONB для эффективного хранения JSON,
    а SQLite использует обычный JSON в текстовом формате. Функционально это то же самое.
    """
    __tablename__ = 'user_preferences'
    
    preference_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, unique=True, index=True, comment="Reference to user")
    
    # ВАЖНОЕ ИЗМЕНЕНИЕ: Вместо JSONB используем JSON
    # SQLite не имеет специального JSONB типа, но обычный JSON работает отлично
    # Вы всё так же можете хранить массивы и объекты в этих полях
    categories = Column(JSON, default=list, nullable=False, comment="Array of selected product categories")
    favorite_shops = Column(JSON, default=list, nullable=False, comment="Array of favorite shops")
    
    price_range_min = Column(Integer, nullable=True, comment="Minimum price filter")
    price_range_max = Column(Integer, nullable=True, comment="Maximum price filter")
    notification_frequency = Column(VARCHAR(20), default='instant', nullable=False, comment="Notification frequency")
    notification_time = Column(Time, nullable=True, comment="Preferred notification time")
    
    def __repr__(self):
        return f"<UserPreference(user={self.user_id}, freq={self.notification_frequency})>"
