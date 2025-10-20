# utils/admin_commands.py (новый файл)

"""
Административные команды для управления ботом.
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from tasks.promotions_updater import update_promotions_task

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("update_promotions"))
async def cmd_update_promotions(message: Message):
    """
    Команда для ручного обновления акций.
    
    Доступна только администраторам.
    """
    # Проверка прав (добавь свой user_id)
    ADMIN_IDS = [123456789]  # Замени на свой ID
    
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Команда доступна только администраторам")
        return
    
    await message.answer("🔄 Запускаю обновление акций...")
    
    try:
        count = await update_promotions_task()
        await message.answer(f"✅ Обновление завершено!\n\nСохранено акций: {count}")
    except Exception as e:
        logger.error(f"Ошибка обновления: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка обновления: {e}")