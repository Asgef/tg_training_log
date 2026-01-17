"""Класс для построения клавиатур тренажёров."""
from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.application.use_case_interfaces import IMachineManagementUseCase
from src.application.dto import MachineLibraryItemDTO
from src.domain.models import MuscleZone, Muscle, Machine


class KeyboardBuilder:
    """Класс для построения inline клавиатур для работы с тренажёрами."""
    
    def __init__(self, machine_management_use_case: IMachineManagementUseCase | None = None):
        """
        Инициализация builder.
        
        Args:
            machine_management_use_case: Use case для работы с тренажёрами (опционально)
        """
        self.use_case = machine_management_use_case
    
    async def build_muscle_zones_keyboard(
        self,
        muscle_zones: List[MuscleZone],
        selected_zone_ids: list[int],
        machine_id: int | None,
        is_creation: bool = False,
    ) -> InlineKeyboardMarkup:
        """
        Построение клавиатуры с зонами и визуальной индикацией.
        
        Args:
            muscle_zones: Список зон
            selected_zone_ids: Список выбранных ID зон
            machine_id: ID тренажёра (None для создания)
            is_creation: True для создания, False для редактирования
            
        Returns:
            InlineKeyboardMarkup с кнопками групп мышц
        """
        keyboard_buttons = []
        
        for zone in muscle_zones:
            is_selected = zone.id in selected_zone_ids
            
            # Выбираем эмодзи в зависимости от статуса
            emoji = "✅" if is_selected else "📦"
            
            if is_creation:
                callback_data = f"select_zone_{zone.id}"
            else:
                callback_data = f"edit_select_zone_{zone.id}"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} {zone.name}",
                    callback_data=callback_data
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🔍 Выбрать отдельные мышцы",
                callback_data="select_individual_muscles" if is_creation else "edit_select_individual_muscles"
            )
        ])
        
        if is_creation:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Завершить и создать тренажер", callback_data="finish_machine_creation")
            ])
            keyboard_buttons.append([
                InlineKeyboardButton(text="⏭️ Пропустить (без мышц)", callback_data="skip_muscle_selection")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_machine_muscles")
            ])
            if machine_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_machine_{machine_id}")
                ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    def build_individual_muscles_keyboard(
        self,
        all_muscles: List[Muscle],
        selected_muscle_ids: list[int],
        machine_id: int | None,
        is_creation: bool = False,
    ) -> InlineKeyboardMarkup:
        """
        Построение клавиатуры с отдельными мышцами.
        
        Args:
            all_muscles: Список всех мышц
            selected_muscle_ids: Список выбранных ID мышц
            machine_id: ID тренажёра (None для создания)
            is_creation: True для создания, False для редактирования
            
        Returns:
            InlineKeyboardMarkup с кнопками отдельных мышц
        """
        keyboard_buttons = []
        
        # Группируем мышцы по зонам (одна мышца -> одна группа отображения)
        muscles_by_group: dict = {}
        for muscle in all_muscles:
            if muscle.zones:
                if len(muscle.zones) == 1:
                    group_name = muscle.zones[0].name
                else:
                    group_name = "Смешанные зоны"
            else:
                group_name = "Без зоны"
            if group_name not in muscles_by_group:
                muscles_by_group[group_name] = []
            muscles_by_group[group_name].append(muscle)
        
        # Создаем клавиатуру с мышцами (по 2 в ряд)
        for group_name, muscles in muscles_by_group.items():
            # Добавляем заголовок группы (если есть несколько групп)
            if len(muscles_by_group) > 1:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📦 {group_name}",
                        callback_data="zone_header"
                    )
                ])
            
            # Добавляем мышцы группы (по 2 в ряд)
            for i in range(0, len(muscles), 2):
                row = []
                muscle = muscles[i]
                is_selected = muscle.id in selected_muscle_ids
                callback_prefix = "toggle_muscle_" if is_creation else "toggle_edit_muscle_"
                row.append(InlineKeyboardButton(
                    text=f"{'✓' if is_selected else '○'} {muscle.name[:20]}",
                    callback_data=f"{callback_prefix}{muscle.id}"
                ))
                if i + 1 < len(muscles):
                    muscle2 = muscles[i+1]
                    is_selected2 = muscle2.id in selected_muscle_ids
                    row.append(InlineKeyboardButton(
                        text=f"{'✓' if is_selected2 else '○'} {muscle2.name[:20]}",
                        callback_data=f"{callback_prefix}{muscle2.id}"
                    ))
                keyboard_buttons.append(row)
        
        # Добавляем кнопки управления
        if is_creation:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Завершить и создать тренажер", callback_data="finish_machine_creation")
            ])
            keyboard_buttons.append([
                InlineKeyboardButton(text="⬅️ Назад к выбору групп", callback_data="add_more_muscles")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_machine_muscles")
            ])
            if machine_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(text="⬅️ Назад к выбору", callback_data=f"edit_machine_muscles_{machine_id}")
                ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    @staticmethod
    def build_machine_details_keyboard(machine_id: int) -> InlineKeyboardMarkup:
        """
        Построение клавиатуры для просмотра деталей тренажёра.
        
        Args:
            machine_id: ID тренажёра
            
        Returns:
            InlineKeyboardMarkup с кнопками управления тренажёром
        """
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_machine_menu_{machine_id}")],
            [InlineKeyboardButton(text="Архивировать", callback_data=f"archive_machine_{machine_id}")],
            [InlineKeyboardButton(text="Назад к списку", callback_data="list_machines")]
        ])
    
    @staticmethod
    def build_machine_list_keyboard(machines: List[Machine]) -> InlineKeyboardMarkup:
        """
        Построение клавиатуры со списком тренажёров.
        
        Args:
            machines: Список тренажёров
            
        Returns:
            InlineKeyboardMarkup с кнопками тренажёров
        """
        keyboard_buttons = []
        for machine in machines:
            keyboard_buttons.append([
                InlineKeyboardButton(text=machine.name, callback_data=f"view_machine_{machine.id}")
            ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    @staticmethod
    def build_machine_edit_menu_keyboard(machine_id: int) -> InlineKeyboardMarkup:
        """
        Построение клавиатуры меню редактирования тренажёра.
        
        Args:
            machine_id: ID тренажёра
            
        Returns:
            InlineKeyboardMarkup с кнопками редактирования
        """
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить название", callback_data=f"edit_machine_name_{machine_id}")],
            [InlineKeyboardButton(text="Изменить фото", callback_data=f"edit_machine_photo_{machine_id}")],
            [InlineKeyboardButton(text="Редактировать зоны/мышцы", callback_data=f"edit_machine_muscles_{machine_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data=f"view_machine_{machine_id}")]
        ])


# Функции-обертки для обратной совместимости
async def build_muscle_zones_keyboard(
    muscle_zones: List[MuscleZone],
    selected_zone_ids: list[int],
    machine_id: int | None,
    machine_management_use_case: IMachineManagementUseCase,
    is_creation: bool = False,
) -> InlineKeyboardMarkup:
    """
    Вспомогательная функция для построения клавиатуры с зонами и визуальной индикацией.
    
    Args:
        muscle_zones: Список зон
        selected_zone_ids: Список выбранных ID зон
        machine_id: ID тренажёра (None для создания)
        machine_management_use_case: Use case для работы с тренажёрами
        is_creation: True для создания, False для редактирования
        
    Returns:
        InlineKeyboardMarkup с кнопками групп мышц
    """
    builder = KeyboardBuilder(machine_management_use_case)
    return await builder.build_muscle_zones_keyboard(
        muscle_zones, selected_zone_ids, machine_id, is_creation
    )


def build_individual_muscles_keyboard(
    all_muscles: List[Muscle],
    selected_muscle_ids: list[int],
    machine_id: int | None,
    is_creation: bool = False,
) -> InlineKeyboardMarkup:
    """
    Построение клавиатуры с отдельными мышцами.
    
    Args:
        all_muscles: Список всех мышц
        selected_muscle_ids: Список выбранных ID мышц
        machine_id: ID тренажёра (None для создания)
        is_creation: True для создания, False для редактирования
        
    Returns:
        InlineKeyboardMarkup с кнопками отдельных мышц
    """
    # Метод build_individual_muscles_keyboard не требует use_case
    builder = KeyboardBuilder()
    return builder.build_individual_muscles_keyboard(
        all_muscles, selected_muscle_ids, machine_id, is_creation
    )


def build_machine_library_list_keyboard(
    machines: List[MachineLibraryItemDTO],
) -> InlineKeyboardMarkup:
    """Клавиатура со списком библиотечных тренажёров."""
    keyboard_buttons = []
    for machine in machines:
        keyboard_buttons.append(
            [InlineKeyboardButton(text=machine.name_ru, callback_data=f"library_machine_{machine.id}")]
        )
    keyboard_buttons.append(
        [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="library_search_again")]
    )
    keyboard_buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="machines_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_machine_library_details_keyboard(
    machine_library_id: int,
) -> InlineKeyboardMarkup:
    """Клавиатура карточки библиотечного тренажёра."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Добавить себе", callback_data=f"add_library_machine_{machine_library_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="library_back_to_results")],
    ])
