.PHONY: seed-muscles seed-muscles-test seed-machines-library help

help:
	@echo "Доступные команды:"
	@echo "  make seed-muscles         - Заполнить базу данных справочной информацией о мышцах и зонах"
	@echo "  make seed-muscles-test    - Заполнить тестовую базу данных (аналогично seed-muscles)"
	@echo "  make seed-machines-library - Заполнить базу данных библиотекой тренажёров"

seed-muscles:
	@echo "Запуск скрипта заполнения справочника мышц..."
	uv run python scripts/seed_muscles.py

seed-muscles-test:
	@echo "Запуск скрипта заполнения тестовой базы данных..."
	uv run python scripts/seed_muscles.py

seed-machines-library:
	@echo "Запуск скрипта заполнения библиотеки тренажёров..."
	uv run python scripts/seed_machines_library.py
