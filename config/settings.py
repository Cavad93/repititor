from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn
from typing import Optional


class Settings(BaseSettings):
    """
    Централизованное хранилище всех настроек приложения.
    
    Использует pydantic для валидации и загрузки из переменных окружения.
    Все чувствительные данные (токены, пароли) должны быть в .env файле,
    никогда не коммитьте их в git.
    """
    
    # Токен Telegram бота из @BotFather
    # Пример: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    BOT_TOKEN: str = Field(..., description="Telegram Bot API Token")
    
    # PostgreSQL настройки базы данных
    # Формат: postgresql://user:password@host:port/database
    POSTGRES_USER: str = Field(default="repititor_user", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="repititor_db", description="PostgreSQL database name")
    
    # Redis настройки для кэширования
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    
    # RabbitMQ для асинхронных задач Celery
    RABBITMQ_HOST: str = Field(default="localhost", description="RabbitMQ host")
    RABBITMQ_PORT: int = Field(default=5672, description="RabbitMQ port")
    RABBITMQ_USER: str = Field(default="guest", description="RabbitMQ username")
    RABBITMQ_PASSWORD: str = Field(default="guest", description="RabbitMQ password")
    
    # Настройки логирования
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: str = Field(default="bot.log", description="Log file path")
    
    # Telegram канал для алертов администраторов
    ADMIN_CHANNEL_ID: Optional[int] = Field(default=None, description="Admin alerts channel ID")
    
    # URL для webhook (опционально, если не используем polling)
    WEBHOOK_URL: Optional[str] = Field(default=None, description="Webhook URL")
    WEBHOOK_PATH: Optional[str] = Field(default="/webhook", description="Webhook path")
    
    # Настройки подписки
    TRIAL_DAYS: int = Field(default=7, description="Trial period in days")
    
    # Elasticsearch для логов (опционально для production)
    ELASTICSEARCH_HOST: Optional[str] = Field(default=None, description="Elasticsearch host")
    ELASTICSEARCH_PORT: Optional[int] = Field(default=9200, description="Elasticsearch port")
    
    @property
    def database_url(self) -> str:
        """
        Формирует полный URL для подключения к PostgreSQL.
        Используется SQLAlchemy для создания engine.
        """
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def redis_url(self) -> str:
        """
        Формирует Redis URL для подключения.
        Если пароль указан, включает его в строку подключения.
        """
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def rabbitmq_url(self) -> str:
        """
        Формирует URL для подключения к RabbitMQ.
        Используется Celery как брокер сообщений.
        """
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"
    
    class Config:
        # Указываем файл с переменными окружения
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Разрешаем использовать значения по умолчанию
        extra = "allow"


# Создаем глобальный экземпляр настроек
# Импортируйте его в других модулях: from config.settings import settings
settings = Settings()