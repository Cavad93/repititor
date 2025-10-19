from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# Base класс для всех моделей SQLAlchemy
# Все таблицы БД будут наследоваться от этого класса
Base = declarative_base()

# Создаем асинхронный engine для работы с PostgreSQL
# echo=False отключает вывод SQL-запросов в консоль (включайте для отладки)
# poolclass=NullPool отключает пул соединений (можно использовать для простоты на старте)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
    future=True
)

# Фабрика для создания асинхронных сессий
# expire_on_commit=False позволяет работать с объектами после commit
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """
    Инициализация базы данных.
    
    Создает все таблицы, определенные в моделях через Base.metadata.
    Эта функция должна вызываться при старте приложения один раз.
    В production лучше использовать миграции Alembic вместо create_all.
    """
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы если их еще нет
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы базы данных успешно созданы/проверены")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise


async def get_session() -> AsyncSession:
    """
    Dependency функция для получения сессии БД.
    
    Использует context manager для автоматического закрытия сессии.
    Пример использования:
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
    
    Должна вызываться при остановке приложения для освобождения ресурсов.
    """
    await engine.dispose()
    logger.info("Соединения с базой данных закрыты")