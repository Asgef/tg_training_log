# Data Model for 001-training-log-bot

This document defines the relational data model for the Telegram Training Log bot, designed for PostgreSQL.

## Table: `users`

Stores information about Telegram users interacting with the bot.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `id`               | BIGINT     | PRIMARY KEY, Telegram User ID                           |
| `is_registered`    | BOOLEAN    | NOT NULL, DEFAULT FALSE, User registration status (FR-001) |
| `google_sheet_url` | TEXT       | NULLABLE, URL to user's Google Sheet (FR-006)           |
| `spreadsheet_id`   | TEXT       | NULLABLE, Google Sheet ID (FR-006)                      |
| `telegram_username`| TEXT       | NULLABLE                                                |
| `telegram_firstname`| TEXT      | NULLABLE                                                |
| `telegram_lastname`| TEXT       | NULLABLE                                                |
| `created_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW(), Record creation timestamp (FR-008) |
| `updated_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW(), Record last update timestamp (FR-008) |
| `timezone`         | TEXT       | NOT NULL, DEFAULT 'Europe/Berlin', User's preferred timezone (FR-008) |

## Table: `muscle_groups`

Stores predefined categories for muscles.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `id`               | SERIAL     | PRIMARY KEY                                             |
| `name`             | TEXT       | NOT NULL, UNIQUE, Name of the muscle group              |
| `created_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |
| `updated_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |

## Table: `muscles`

Stores individual muscle names, linked to muscle groups.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `id`               | SERIAL     | PRIMARY KEY                                             |
| `name`             | TEXT       | NOT NULL, UNIQUE, Name of the muscle                    |
| `group_id`         | INTEGER    | NOT NULL, FOREIGN KEY REFERENCES `muscle_groups(id)`    |
| `created_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |
| `updated_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |

## Table: `machines`

Stores personal exercise machines/equipment defined by each user.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `id`               | SERIAL     | PRIMARY KEY                                             |
| `user_id`          | BIGINT     | NOT NULL, FOREIGN KEY REFERENCES `users(id)`, Owner of the machine (FR-004) |
| `name`             | TEXT       | NOT NULL, (FR-009: `имя тренажёра не пустое`)           |
| `photo_file_id`    | TEXT       | NULLABLE, Telegram `file_id` for machine photo (A-002)  |
| `is_archived`      | BOOLEAN    | NOT NULL, DEFAULT FALSE, Indicates if machine is archived |
| `created_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |
| `updated_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |
| `CONSTRAINT uq_user_machine_name` | UNIQUE(user_id, name) | Ensures a user has unique machine names |

## Table: `machine_muscles`

Junction table for many-to-many relationship between `machines` and `muscles`.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `machine_id`       | INTEGER    | NOT NULL, FOREIGN KEY REFERENCES `machines(id)`         |
| `muscle_id`        | INTEGER    | NOT NULL, FOREIGN KEY REFERENCES `muscles(id)`          |
| `PRIMARY KEY`      |            | (`machine_id`, `muscle_id`)                             |

## Table: `workout_sessions`

Records individual workout sessions.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `id`               | SERIAL     | PRIMARY KEY                                             |
| `user_id`          | BIGINT     | NOT NULL, FOREIGN KEY REFERENCES `users(id)`            |
| `started_at`       | TIMESTAMPTZ| NOT NULL, Session start timestamp                       |
| `ended_at`         | TIMESTAMPTZ| NULLABLE, Session end timestamp (NULL if active) (FR-003) |
| `created_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |
| `updated_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |

## Table: `set_entries`

Records individual sets/approaches within a workout session.

| Column Name        | Type       | Constraints / Description                               |
|--------------------|------------|---------------------------------------------------------|
| `id`               | SERIAL     | PRIMARY KEY                                             |
| `session_id`       | INTEGER    | NOT NULL, FOREIGN KEY REFERENCES `workout_sessions(id)`, Linked to active session (FR-005) |
| `machine_id`       | INTEGER    | NOT NULL, FOREIGN KEY REFERENCES `machines(id)`         |
| `weight`           | NUMERIC(5,2)| NOT NULL, (FR-009: `weight > 0`)                       |
| `reps`             | INTEGER    | NOT NULL, (FR-009: `reps > 0`)                          |
| `failure`          | BOOLEAN    | NOT NULL, DEFAULT FALSE, Indicates if set was to failure |
| `created_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |
| `updated_at`       | TIMESTAMPTZ| NOT NULL, DEFAULT NOW()                                 |