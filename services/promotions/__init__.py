# services/promotions/__init__.py

"""
Модуль для работы с акциями и промокодами.
"""

from .edadeal_parser import EdadealParser
from .base_parser import BasePromotionParser

__all__ = [
    'EdadealParser',
    'BasePromotionParser',
]