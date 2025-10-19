# services/affiliate/__init__.py
from .base import AffiliateServiceBase
from .admitad import AdmitadService

__all__ = [
    'AffiliateServiceBase',
    'AdmitadService'
]
