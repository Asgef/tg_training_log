"""FSM states для управления тренажёрами."""
from aiogram.fsm.state import State, StatesGroup


class MachineStates(StatesGroup):
    """Состояния FSM для процесса создания/редактирования тренажёров."""
    waiting_for_machine_name = State()
    waiting_for_machine_photo = State()
    waiting_for_muscle_selection = State()
    waiting_for_edit_name = State()
    waiting_for_edit_photo = State()
    waiting_for_edit_muscle_selection = State()
    waiting_for_library_search_query = State()
