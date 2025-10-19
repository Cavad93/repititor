from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# Base класс для всех моделей SQLAlchemy
# Все таблицы БД будут наследоваться от этого класса
# Это не изменилось - Base работает одинаково для любой базы данных
Base = declarative_base()

# Создаем асинхронный engine для работы с SQLite
# ИЗМЕНЕНО: Вместо asyncpg драйвера для PostgreSQL используем aiosqlite для SQLite
# 
# Ключевые изменения:
# - URL базы теперь sqlite+aiosqlite:/// вместо postgresql+asyncpg://
# - Убрали poolclass=NullPool потому что SQLite не поддерживает пулы соединений
# - Добавили connect_args с check_same_thread=False для работы в асинхронном режиме
#
# SQLite по умолчанию разрешает работу только из одного потока, но наш бот
# асинхронный и может обрабатывать множество запросов одновременно.
# Параметр check_same_thread=False отключает эту проверку.
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Установите True для отладки - будут видны все SQL запросы
    connect_args={"check_same_thread": False},  # Важно для SQLite в асинхронном режиме
    future=True
)

# Фабрика для создания асинхронных сессий
# Это не изменилось - работает одинаково для PostgreSQL и SQLite
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """
    Инициализация базы данных.
    
    ИЗМЕНЕНО: Теперь эта функция не только создает таблицы, но и автоматически
    создает файл базы данных если его еще нет. С PostgreSQL файл не создавался
    потому что база управлялась сервером, а с SQLite мы сами создаем файл.
    
    При первом запуске бота файл repititor.db появится в папке проекта
    и в нем будут созданы все необходимые таблицы.
    """
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы если их еще нет
            # CREATE TABLE IF NOT EXISTS выполняется для каждой модели
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info(f"База данных SQLite успешно инициализирована: {settings.DATABASE_PATH}")
        logger.info("Все таблицы созданы и готовы к работе")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise


async def get_session() -> AsyncSession:
    """
    Dependency функция для получения сессии БД.
    
    НЕ ИЗМЕНИЛОСЬ: Эта функция работает абсолютно одинаково для любой БД.
    SQLAlchemy предоставляет универсальный интерфейс для работы с сессиями.
    
    Использование:
        async with get_session() as session:
            result = await session.execute(query)
    
    Returns:
        AsyncSession: Асинхронная сессия для работы с БД
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка в сессии БД: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """
    Корректное закрытие всех соединений с базой данных.
    
    НЕ ИЗМЕНИЛОСЬ: Для любой базы данных важно корректно закрывать соединения
    при остановке приложения чтобы освободить ресурсы и избежать повреждения данных.
    
    Должна вызываться при остановке приложения.
    """
    await engine.dispose()
    logger.info("Соединения с базой данных закрыты")
