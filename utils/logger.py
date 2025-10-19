import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
import json

from config.settings import settings


class JSONFormatter(logging.Formatter):
    """
    Кастомный форматтер для вывода логов в формате JSON.
    
    JSON формат логов упрощает их обработку и анализ в системах мониторинга
    таких как Elasticsearch, Logstash, Kibana (ELK stack).
    Каждая запись лога становится структурированным объектом с четкими полями.
    
    Преимущества JSON логов:
    - Легко парсятся автоматическими системами
    - Поддерживают вложенные структуры данных
    - Удобны для поиска и фильтрации в Kibana
    - Стандартизированный формат для микросервисов
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Преобразует запись лога в JSON формат.
        
        Эта функция вызывается автоматически для каждой записи лога.
        Она извлекает все важные поля из record и упаковывает их в JSON объект.
        
        Args:
            record: Объект записи лога с информацией о событии
            
        Returns:
            str: JSON строка с форматированной информацией о событии
        """
        # Создаем словарь с основными полями лога
        log_data = {
            # Временная метка когда произошло событие
            'timestamp': datetime.utcnow().isoformat(),
            
            # Уровень важности сообщения (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            'level': record.levelname,
            
            # Имя логгера (обычно имя модуля откуда идет лог)
            'logger': record.name,
            
            # Само сообщение лога
            'message': record.getMessage(),
            
            # Имя файла где произошло событие
            'file': record.pathname,
            
            # Номер строки в файле
            'line': record.lineno,
            
            # Имя функции откуда вызван лог
            'function': record.funcName
        }
        
        # Если есть информация об исключении - добавляем её
        # exc_info содержит информацию о traceback при ошибках
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Если есть дополнительные поля (через logging.info("msg", extra={...}))
        # добавляем их в отдельный раздел
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        # Преобразуем словарь в JSON строку
        # ensure_ascii=False позволяет сохранять кириллицу без экранирования
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Форматтер для цветного вывода логов в консоль.
    
    Разные уровни логов отображаются разными цветами для лучшей читаемости:
    - DEBUG: серый
    - INFO: зеленый
    - WARNING: желтый
    - ERROR: красный
    - CRITICAL: красный на белом фоне (инвертированный)
    
    Цвета используют ANSI escape коды, которые работают в большинстве терминалов
    Linux, macOS и Windows Terminal. В старых версиях Windows CMD цвета могут не работать.
    """
    
    # ANSI коды цветов для терминала
    # Формат: \033[код_цветаm где код определяет цвет текста
    grey = "\x1b[38;21m"      # Серый для DEBUG
    green = "\x1b[32;21m"     # Зеленый для INFO
    yellow = "\x1b[33;21m"    # Желтый для WARNING
    red = "\x1b[31;21m"       # Красный для ERROR
    bold_red = "\x1b[31;1m"   # Жирный красный для CRITICAL
    reset = "\x1b[0m"         # Сброс цвета
    
    # Определяем формат сообщения для каждого уровня логирования
    # %(levelname)s - уровень лога
    # %(name)s - имя логгера (модуль)
    # %(message)s - текст сообщения
    format_string = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    
    # Словарь соответствия уровней логирования и их цветов
    FORMATS = {
        logging.DEBUG: grey + format_string + reset,
        logging.INFO: green + format_string + reset,
        logging.WARNING: yellow + format_string + reset,
        logging.ERROR: red + format_string + reset,
        logging.CRITICAL: bold_red + format_string + reset
    }
    
    def format(self, record):
        """
        Применяет цветной формат к записи лога в зависимости от его уровня.
        
        Args:
            record: Объект записи лога
            
        Returns:
            str: Отформатированная цветная строка лога
        """
        # Получаем формат для текущего уровня логирования
        log_fmt = self.FORMATS.get(record.levelno)
        
        # Создаем форматтер с нужным форматом
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        
        # Применяем форматирование и возвращаем результат
        return formatter.format(record)


def setup_logging():
    """
    Настраивает систему логирования для всего приложения.
    
    Эта функция создает два типа обработчиков логов:
    1. Console handler - выводит логи в консоль с цветным форматированием (для разработки)
    2. File handler - сохраняет логи в файл в JSON формате (для production и анализа)
    
    Функция должна вызываться один раз при старте приложения в main.py
    
    Структура логирования:
    - Уровень логирования определяется настройками (по умолчанию INFO)
    - Логи ротируются по размеру (не более 10MB на файл)
    - Хранятся последние 5 файлов логов
    - Критические ошибки дублируются в отдельный файл
    """
    
    # Создаем директорию для логов если её нет
    # Path создает объект пути, mkdir создает директорию
    # parents=True создаст все промежуточные директории
    # exist_ok=True не вызовет ошибку если директория уже существует
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Получаем корневой логгер - родитель всех логгеров в приложении
    # Настройки корневого логгера применяются ко всем дочерним логгерам
    root_logger = logging.getLogger()
    
    # Устанавливаем уровень логирования из настроек
    # Уровни по важности: DEBUG < INFO < WARNING < ERROR < CRITICAL
    # Если установлен INFO, то DEBUG сообщения не будут логироваться
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Очищаем существующие обработчики если они есть
    # Это предотвращает дублирование логов при повторном вызове setup_logging
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # === НАСТРОЙКА КОНСОЛЬНОГО ВЫВОДА ===
    # StreamHandler выводит логи в поток (в данном случае в stdout - консоль)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Консоль показывает все логи включая DEBUG
    
    # Применяем цветной форматтер для удобной разработки
    console_handler.setFormatter(ColoredFormatter())
    
    # Добавляем обработчик к корневому логгеру
    root_logger.addHandler(console_handler)
    
    # === НАСТРОЙКА ФАЙЛОВОГО ЛОГИРОВАНИЯ (ОБЩИЕ ЛОГИ) ===
    # RotatingFileHandler автоматически создает новый файл когда текущий достигает maxBytes
    # Это предотвращает рост файла до бесконечности
    file_handler = RotatingFileHandler(
        log_dir / "bot.log",        # Путь к файлу лога
        maxBytes=10 * 1024 * 1024,  # Максимальный размер файла: 10MB
        backupCount=5,               # Хранить последние 5 файлов
        encoding='utf-8'             # Кодировка для поддержки кириллицы
    )
    file_handler.setLevel(logging.INFO)  # В файл пишем только INFO и выше (не DEBUG)
    
    # Используем JSON форматтер для структурированных логов
    # Это удобно для последующей обработки в системах мониторинга
    file_handler.setFormatter(JSONFormatter())
    
    # Добавляем файловый обработчик к корневому логгеру
    root_logger.addHandler(file_handler)
    
    # === НАСТРОЙКА ФАЙЛОВОГО ЛОГИРОВАНИЯ (ТОЛЬКО ОШИБКИ) ===
    # Создаем отдельный файл для критических ошибок
    # Это упрощает поиск проблем - не нужно просматривать весь лог
    error_file_handler = RotatingFileHandler(
        log_dir / "errors.log",     # Отдельный файл для ошибок
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    # Этот обработчик логирует только ERROR и CRITICAL
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(JSONFormatter())
    
    root_logger.addHandler(error_file_handler)
    
    # === НАСТРОЙКА ДНЕВНОГО РОТИРОВАНИЯ (ОПЦИОНАЛЬНО) ===
    # TimedRotatingFileHandler создает новый файл каждый день
    # Удобно для долгосрочного хранения и анализа логов по датам
    daily_handler = TimedRotatingFileHandler(
        log_dir / "bot_daily.log",
        when='midnight',           # Ротация в полночь
        interval=1,                # Каждый день
        backupCount=30,            # Хранить логи за последние 30 дней
        encoding='utf-8'
    )
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(JSONFormatter())
    
    root_logger.addHandler(daily_handler)
    
    # Логируем успешную инициализацию системы логирования
    root_logger.info("Система логирования инициализирована")
    root_logger.info(f"Уровень логирования: {settings.LOG_LEVEL}")
    root_logger.info(f"Логи сохраняются в директорию: {log_dir.absolute()}")


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер с указанным именем.
    
    Эта функция - удобная обертка для logging.getLogger().
    В модулях импортируйте так: logger = get_logger(__name__)
    
    __name__ автоматически содержит имя текущего модуля,
    что помогает идентифицировать откуда пришло сообщение лога.
    
    Пример использования в модуле handlers/menu.py:
        from utils.logger import get_logger
        logger = get_logger(__name__)  # Создаст логгер с именем "handlers.menu"
        logger.info("Пользователь открыл меню")
    
    Args:
        name: Имя логгера (обычно __name__ модуля)
        
    Returns:
        logging.Logger: Настроенный объект логгера
    """
    return logging.getLogger(name)