from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """
    Централизованное хранилище всех настроек приложения.
    
    ИЗМЕНЕНО: Убрали все настройки PostgreSQL, Redis и RabbitMQ.
    Теперь используется SQLite который не требует никаких настроек подключения.
    База данных создается автоматически в папке проекта.
    """
    
    # Токен Telegram бота из @BotFather
    # Пример: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    BOT_TOKEN: str = Field(..., description="Telegram Bot API Token")
    
    # Путь к файлу базы данных SQLite
    # По умолчанию создается в папке проекта с именем repititor.db
    # Вы можете изменить это на любой другой путь если нужно
    DATABASE_PATH: str = Field(
        default="repititor.db", 
        description="Path to SQLite database file"
    )
    
    # Настройки логирования остаются прежними
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: str = Field(default="bot.log", description="Log file path")
    
    # Telegram канал для алертов администраторов (опционально)
    ADMIN_CHANNEL_ID: Optional[int] = Field(
        default=None, 
        description="Admin alerts channel ID"
    )
    
    # URL для webhook (опционально, если не используем polling)
    WEBHOOK_URL: Optional[str] = Field(
        default=None, 
        description="Webhook URL"
    )
    WEBHOOK_PATH: Optional[str] = Field(
        default="/webhook", 
        description="Webhook path"
    )
    
    # Настройки подписки
    TRIAL_DAYS: int = Field(
        default=7, 
        description="Trial period in days"
    )
    
    
# ==================== ПАРТНЕРСКИЕ ПРОГРАММЫ ====================
    
    # Admitad - единственная партнерская программа
    ADMITAD_AUTH_HEADER: Optional[str] = Field(
        default=None,
        description="Admitad Base64 Authorization Header (включая 'Basic ')"
    )
    ADMITAD_WEBSITE_ID: Optional[str] = Field(
        default=None,
        description="Admitad Website/Client ID (строковый идентификатор площадки)"
    )
    
    # Настройки кэшбэка
    MIN_WITHDRAWAL_AMOUNT: int = Field(
        default=500,
        description="Minimum withdrawal amount in rubles"
    )
    CASHBACK_CONFIRMATION_DAYS: int = Field(
        default=30,
        description="Days to wait for cashback confirmation"
    )


    @property
    def database_url(self) -> str:
        """
        Формирует URL для подключения к SQLite базе данных.
        
        ИЗМЕНЕНО: Вместо сложного URL для PostgreSQL с хостом, портом, 
        пользователем и паролем, SQLite использует простой путь к файлу.
        Формат: sqlite+aiosqlite:///путь/к/файлу.db
        
        Три слэша /// означают абсолютный путь, четыре //// для Windows путей.
        Мы используем относительный путь, поэтому три слэша достаточно.
        """
        # Преобразуем путь в абсолютный для надежности
        db_path = Path(self.DATABASE_PATH).absolute()
        # Для Windows путей нужен специальный формат с тремя слэшами
        return f"sqlite+aiosqlite:///{db_path}"
    
    class Config:
        # Указываем файл с переменными окружения
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Разрешаем использовать значения по умолчанию
        extra = "allow"


# Создаем глобальный экземпляр настроек
# Импортируйте его в других модулях: from config.settings import settings
settings = Settings()
