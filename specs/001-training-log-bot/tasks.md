---
description: "Task list for feature 001-training-log-bot. All tasks align with the principles defined in .specify/memory/constitution.md."
---

# Tasks: 001-training-log-bot

**Input**: Design documents from `/specs/001-training-log-bot/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Paths assume a single project structure with `src/` at the root.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure.

- [X] T001 Создать директории проекта: `src/`, `tests/`, `scripts/`, `src/domain`, `src/application`, `src/infrastructure`, `src/infrastructure/web`, `src/infrastructure/db`, `src/infrastructure/services`, `src/configs`
- [X] T002 Инициализировать Python проект с помощью `uv` и создать `pyproject.toml`
- [X] T003 [P] Добавить основные зависимости в `pyproject.toml`: `aiogram`, `psycopg2-binary`, `SQLAlchemy`, `alembic`, `google-api-python-client`, `gspread`, `pandas`, `python-dotenv`
- [X] T004 [P] Создать `README.md` для обзора проекта.
- [X] T005 Создать `docker-compose.yml` для сервиса базы данных PostgreSQL.
- [X] T006 Создать `.env.example` файл для переменных окружения (`BOT_TOKEN`, `DATABASE_URL`, `ADMIN_ID`, `GOOGLE_CREDENTIALS_JSON`).


---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

- [X] T007 Конфигурировать Alembic для миграций базы данных в `src/infrastructure/db/`
- [X] T009 Create initial migration script with all tables from `data-model.md` using Alembic.
- [X] T010 [P] Определить все доменные модели (`User`, `Muscle`, `Machine`, etc.) в `src/domain/models.py`.
- [X] T011 [P] Определить интерфейсы репозиториев в `src/application/repositories.py` на основе `contracts/repository_interfaces.py`.
- [X] T012 [P] Define use case interfaces in `src/application/use_cases.py` based on `contracts/use_case_interfaces.py`.
- [X] T013 Implement `main.py` to initialize the `aiogram` dispatcher, bot, and setup a basic dependency injection container.
- [X] T014 Implement a basic logging configuration in `src/configs/logging_config.py`.

---

## Phase 3: User Story 1 - Registration and Access (Priority: P1) 🎯 MVP

**Goal**: A new user can request access, and an admin can approve or deny it.
**Independent Test**: A new user can send `/start`, request registration, get approved by an admin, and receive a confirmation message.

### Implementation for User Story 1

- [X] T015 [US1] Implement `UserRepository` in `src/infrastructure/db/repositories/user_repository.py`.
- [X] T016 [US1] Implement `RegistrationUseCase` in `src/application/use_cases/registration.py`, depending on `IUserRepository`.
- [X] T017 [US1] Implement Telegram handlers for `/start`, registration request, and admin approval/rejection callbacks in `src/infrastructure/web/handlers/registration.py`.
- [X] T018 [US1] Implement a middleware in `src/infrastructure/web/middlewares.py` to check user's `is_registered` status for protected commands.
- [X] T019 [US1] Register handlers and middleware in `main.py`.

---

## Phase 4: User Story 2 - Manage workouts and sets (Priority: P1)

**Goal**: User can start/stop a workout session and record sets.
**Independent Test**: User starts a workout, records two sets, and ends the workout. The data is correctly saved.

### Implementation for User Story 2

- [X] T020 [P] [US2] Implement `WorkoutSessionRepository` in `src/infrastructure/db/repositories/workout_session_repository.py`.
- [X] T021 [P] [US2] Implement `SetEntryRepository` in `src/infrastructure/db/repositories/set_entry_repository.py`.
- [X] T022 [US2] Implement `WorkoutUseCase` in `src/application/use_cases/workout.py`.
- [X] T023 [US2] Implement Telegram handlers for starting/ending workouts and recording sets in `src/infrastructure/web/handlers/workout.py`.
- [X] T024 [US2] Register new handlers in `main.py`.

---

## Phase 5: User Story 3 - Manage machine catalog (Priority: P2)

**Goal**: User can create, view, edit, and archive their personal machines.
**Independent Test**: A user adds a new machine, views it in their list, and then archives it.

### Implementation for User Story 3

- [X] T025 [P] [US3] Implement `MachineRepository` in `src/infrastructure/db/repositories/machine_repository.py`.
- [X] T026 [P] [US3] Implement `MuscleRepository` in `src/infrastructure/db/repositories/muscle_repository.py`.
- [X] T027 [US3] Implement `MachineManagementUseCase` in `src/application/use_cases/machine_management.py`.
- [X] T028 [US3] Implement Telegram handlers for machine CRUD operations (add, view, list, edit, archive) in `src/infrastructure/web/handlers/machine.py`.
- [X] T029 [US3] Register new machine-related handlers in `main.py`.

---

## Phase 6: User Story 4 - Export to Google Sheets (Priority: P2)

**Goal**: User can connect their Google Sheet and export their workout data.
**Independent Test**: User provides a sheet URL, gives access, and successfully exports their machine list and workout log.

### Implementation for User Story 4

- [X] T030 [US4] Implement a Google Sheets client in `src/infrastructure/services/google_sheets_client.py` using `gspread` and `pandas`.
- [X] T031 [US4] Implement `GoogleSheetsExportUseCase` in `src/application/use_cases/google_sheets_export.py`.
- [X] T032 [US4] Implement Telegram handlers for setting up Google Sheets and triggering the export in `src/infrastructure/web/handlers/common.py`.
- [X] T033 [US4] Update `UserRepository` to save Google Sheets configuration.
- [X] T034 [US4] Register new handlers in `main.py`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [X] T035 [P] Enhance logging across all use cases and handlers for better audit trails.
- [X] T036 Просмотреть и рефакторить код для ясности, производительности и соответствия принципам чистой архитектуры.
- [X] T037 [P] Обновить `README.md` подробными инструкциями по настройке, руководством по переменным окружения и примерами использования.
- [X] T038 Проверить все пользовательские истории и критерии приемки из `spec.md`. (Требуется ручное тестирование бота)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. BLOCKS all user stories.
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 & US2 (P1)**: Can start in parallel after Phase 2.
- **US3 & US4 (P2)**: Can start in parallel after Phase 2. It's recommended to complete P1 stories first.
- **US3** depends on **US1** for `user_id`.
- **US4** depends on **US1** for `user_id` and can be enhanced by data from **US2** and **US3**.

### Parallel Opportunities

- **Setup**: T003, T004, T005 can run in parallel.
- **Foundational**: T010, T011, T012 can run in parallel.
- **User Stories**: Once Foundational is done, different developers can take on different user stories (e.g., Dev A on US1, Dev B on US2).
- Within stories, repository implementations (e.g., T020, T021) can often be done in parallel.

---

## Implementation Strategy

### MVP First (P1 Stories)

1.  Complete Phase 1: Setup
2.  Complete Phase 2: Foundational
3.  Complete Phase 3: User Story 1 (Registration)
4.  Complete Phase 4: User Story 2 (Workouts)
5.  **STOP and VALIDATE**: Test the core functionality of registration and workout logging.

### Incremental Delivery

1.  Complete Setup + Foundational.
2.  Add User Story 1 & 2 -> Deploy/Demo (Core MVP).
3.  Add User Story 3 -> Deploy/Demo (Adds machine management).
4.  Add User Story 4 -> Deploy/Demo (Adds export feature).
