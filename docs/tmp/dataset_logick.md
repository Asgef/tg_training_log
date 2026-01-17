# ТЗ: Датасет и выгрузка в Google Sheets (на базе БД v2)

## 1) Цель

Реализовать выгрузку данных из БД v2 в Google Spreadsheet пользователя так, чтобы:

* формировался **стабильный датасет нагрузки** (история не меняется при редактировании тренажёров);
* данные на листах были **удобны для графиков, сводных, BI и ML**;
* выгрузка была **идемпотентной** (повторный запуск не создаёт дубликаты).

---

## 2) Подключение таблицы

### 2.1 Модель доступа

* Используется **Google Service Account**.
* Пользователь предоставляет ссылку на Spreadsheet.
* Если нет прав записи: бот сообщает сервисный email и просит дать **Editor**.

### 2.2 Что хранится в БД по подключению

В `users` заполняются:

* `google_sheet_url`
* `spreadsheet_id`
  (при необходимости допускается хранить только `spreadsheet_id`, но `url` удобен для UI)

---

## 3) Структура Spreadsheet

В Spreadsheet должны существовать листы:

1. `LOG_SETS` — журнал подходов (append-only)
2. `LOG_MUSCLES` — датасет нагрузки по мышцам (append-only)
3. `REF_MACHINES` — справочник тренажёров/упражнений (обновляемый)
4. `REF_ZONES` — справочник зон (обновляемый)
5. `REF_MUSCLES` — справочник мышц (обновляемый)
6. `REF_ZONE_MUSCLES` — связь зона↔мышца (обновляемый)

Если лист отсутствует — создаётся автоматически.
Необходимы заголовки, названия листов, в начале листа на русском языке
После строки с заголовком Названием листа, продублировать заголовки колонок на русском языке. Далее всё как в пунктах ниже
---

## 4) Лист `LOG_SETS` (append-only)

### 4.1 Назначение

Хранить “сырые события”: каждый подход — одна строка.

### 4.2 Правило записи

* Всегда **добавлять новые строки в конец**.
* **Ничего не перезаписывать** (история).
* Запрещено создавать дубликаты по `set_id`.

### 4.3 Колонки (строго в этом порядке)

1. `set_id`
2. `performed_at` (ISO datetime)
3. `date` (YYYY-MM-DD)
4. `time` (HH:MM:SS)
5. `session_id`
6. `machine_id`
7. `machine_name`
8. `weight_kg`
9. `reps`
10. `rir` (0..5)
11. `volume` (weight_kg * reps)

### 4.4 Источник данных (БД)

* `set_id` ← `set_entries.id`
* `performed_at` ← `set_entries.created_at`
* `session_id` ← `set_entries.session_id`
* `machine_id` ← `set_entries.machine_id`
* `machine_name` ← `machines.name`
* `weight_kg` ← `set_entries.weight`
* `reps` ← `set_entries.reps`
* `rir` ← `set_entries.rir`
* `volume` ← вычисляемое

---

## 5) Лист `LOG_MUSCLES` (append-only)

### 5.1 Назначение

Это основной датасет “нагрузка на мышцы” для аналитики и ML.
**Одна строка = одна мышца в одном подходе.**

### 5.2 Правило записи

* Всегда **добавлять новые строки в конец**.
* **Ничего не перезаписывать**.
* Запрещено создавать дубликаты по ключу (`set_id`, `muscle_id`).

### 5.3 Колонки (строго в этом порядке)

1. `set_id`
2. `performed_at` (ISO datetime)
3. `date` (YYYY-MM-DD)
4. `time` (HH:MM:SS)
5. `session_id`
6. `machine_id`
7. `machine_name`
8. `muscle_id`
9. `muscle_name`
10. `weight_kg`
11. `reps`
12. `rir` (0..5)
13. `volume` (weight_kg * reps)

> Примечание: зоны в `LOG_MUSCLES` **не обязательны** — они легко подтягиваются через справочник.
> Можно добавить колонки `zone_names_snapshot` (строкой) — см. п. 5.6.

### 5.4 Источник данных (БД)

* `set_id` ← `set_entries.id`
* `performed_at/date/time` ← `set_entries.created_at`
* `session_id` ← `set_entries.session_id`
* `machine_id` ← `set_entries.machine_id`
* `machine_name` ← `machines.name`
* `muscle_id` ← `set_entry_muscles.muscle_id`
* `muscle_name` ← `muscles.name`
* `weight/reps/rir` ← `set_entries.*`
* `volume` ← вычисляемое

### 5.5 Требование стабильности истории

`LOG_MUSCLES` формируется **только** через snapshot `set_entry_muscles`.
### 5.6 (Опционально) Снимок зон в датасете

В конец `LOG_MUSCLES` добавить:
14. `zone_names_snapshot` (строка, через запятую)

Источник: `set_entry_zones` + `muscle_zones.name`.

---

## 6) Лист `REF_MACHINES` (обновляемый справочник)

### 6.1 Назначение

Справочник упражнений/тренажёров пользователя для удобной фильтрации и join’ов.

### 6.2 Правило записи

* Лист приводится к **актуальному состоянию** (допускается полная перезапись).
* Ключ: `machine_id`.

### 6.3 Колонки

1. `machine_id`
2. `machine_name`
3. `is_archived` (TRUE/FALSE)
4. `zone_names_current` (строка)
5. `muscle_names_current` (строка)
6. `updated_at` (ISO datetime)

### 6.4 Источник (БД)

* `machine_id` ← `machines.id`
* `machine_name` ← `machines.name`
* `is_archived` ← `machines.is_archived`
* `zone_names_current` ← `machine_zones` + `muscle_zones.name`
* `muscle_names_current` ← `machine_muscles` + `muscles.name`
* `updated_at` ← `machines.updated_at`

---

## 7) Листы справочников зон/мышц (обновляемые)

### 7.1 `REF_ZONES`

Колонки:

1. `zone_id`
2. `zone_name`
3. `updated_at`

Источник: `muscle_zones`.

### 7.2 `REF_MUSCLES`

Колонки:

1. `muscle_id`
2. `muscle_name`
3. `updated_at`

Источник: `muscles`.

### 7.3 `REF_ZONE_MUSCLES`

Колонки:

1. `zone_id`
2. `zone_name`
3. `muscle_id`
4. `muscle_name`

Источник: `muscle_zone_muscles` + join на `muscle_zones` и `muscles`.

Правило: допускается полная перезапись.

---

## 8) Идемпотентность выгрузки (без дублей)

### 8.1 Принцип

Повторный запуск “Выгрузить данные” не должен добавлять уже выгруженные строки в `LOG_SETS` и `LOG_MUSCLES`.

### 8.2 Опорный ключ

* Для `LOG_SETS`: `set_id`
* Для `LOG_MUSCLES`: (`set_id`, `muscle_id`)

### 8.3 Маркер выгрузки

Система должна иметь механизм определения “какие set_id уже выгружены”.
Допускаются варианты:

* хранить маркер в БД у пользователя (например `last_exported_set_id` или `last_exported_at`);
* или читать последнюю строку листа и брать максимальный `set_id` (если гарантируется монотонность id).

В рамках ТЗ: требуется обеспечить отсутствие дублей, способ реализации выбирается разработчиком.

---

## 9) Ошибки и сообщения пользователю (UI требования)

* Если таблица не подключена: сообщить, что нужно подключить Google Sheets.
* Если нет доступа: сообщить, что нужно дать Editor доступ сервисному email.
* Если выгрузка успешна: сообщить “выгрузка выполнена” + сколько строк добавлено в `LOG_SETS` и `LOG_MUSCLES`.

---

## 10) Критерии готовности (DoD)

Считается выполненным, если:

* Создаются/поддерживаются все листы, перечисленные в п.3;
* `LOG_SETS` и `LOG_MUSCLES` пополняются только новыми строками, без дублей;
* `LOG_MUSCLES` строится из snapshot `set_entry_muscles` (история стабильна);
* `REF_*` листы отражают актуальное состояние справочников/тренажёров;
* Пользователь получает понятные сообщения при ошибках доступа и при успехе.

