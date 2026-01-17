"""Модуль обработчиков для управления тренажёрами."""
from aiogram import Router

from src.infrastructure.web.handlers.machine import create, edit, view, library

# Создаём главный роутер для модуля machine
router = Router()

# Включаем подроутеры
router.include_router(create.router)
router.include_router(edit.router)
router.include_router(view.router)
router.include_router(library.router)

__all__ = ["router"]
