from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """
    Состояния FSM для процесса анкетирования пользователя.
    
    FSM (Finite State Machine) позволяет отслеживать на каком этапе
    анкетирования находится пользователь и корректно обрабатывать его ответы.
    
    Каждое состояние соответствует одному экрану анкеты:
    - categories: выбор интересующих категорий товаров
    - shops: выбор предпочитаемых магазинов
    - price_range: определение ценового диапазона
    - notifications: настройка частоты и времени уведомлений
    - notification_time: выбор времени для дайджеста (если применимо)
    - summary: показ итоговой сводки перед сохранением
    """
    
    categories = State()
    shops = State()
    price_range = State()
    notifications = State()
    notification_time = State()
    summary = State()


class SettingsEditStates(StatesGroup):
    """
    Состояния FSM для редактирования настроек.
    
    Используется когда пользователь хочет изменить свои предпочтения
    через раздел "Настройки" без полного прохождения анкеты заново.
    """
    
    edit_categories = State()
    edit_shops = State()
    edit_price_range = State()
    edit_notifications = State()
    edit_notification_time = State()