"""Клавиатуры для UI записи подхода."""
from __future__ import annotations

from typing import Sequence
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.application.dto import MachineDTO


def build_machine_selection_keyboard(
    recent_machines: Sequence[MachineDTO],
    other_machines: Sequence[MachineDTO],
) -> InlineKeyboardMarkup:
    """Строит клавиатуру выбора тренажера."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for machine in list(recent_machines) + list(other_machines):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=machine.name,
                    callback_data=f"machine_select:{machine.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="🔍 Найти по названию",
                callback_data="machine_search",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_set_params_keyboard() -> InlineKeyboardMarkup:
    """Строит клавиатуру изменения параметров подхода."""
    keyboard = [
        [
            InlineKeyboardButton(text="-1", callback_data="set_weight:-1"),
            InlineKeyboardButton(text="-5", callback_data="set_weight:-5"),
            InlineKeyboardButton(text="+5", callback_data="set_weight:+5"),
            InlineKeyboardButton(text="+1", callback_data="set_weight:+1"),
        ],
        [InlineKeyboardButton(text="Ввести вручную", callback_data="set_manual_weight")],
        [
            InlineKeyboardButton(text="-1", callback_data="set_reps:-1"),
            InlineKeyboardButton(text="-5", callback_data="set_reps:-5"),
            InlineKeyboardButton(text="+5", callback_data="set_reps:+5"),
            InlineKeyboardButton(text="+1", callback_data="set_reps:+1"),
        ],
        [InlineKeyboardButton(text="Ввести вручную", callback_data="set_manual_reps")],
        [
            InlineKeyboardButton(text="RIR 0", callback_data="set_rir:0"),
            InlineKeyboardButton(text="RIR 1", callback_data="set_rir:1"),
            InlineKeyboardButton(text="RIR 2", callback_data="set_rir:2"),
        ],
        [
            InlineKeyboardButton(text="RIR 3", callback_data="set_rir:3"),
            InlineKeyboardButton(text="RIR 4", callback_data="set_rir:4"),
            InlineKeyboardButton(text="RIR 5", callback_data="set_rir:5"),
        ],
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="set_save"),
            InlineKeyboardButton(text="✏️ Сбросить", callback_data="set_reset"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="set_cancel"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
