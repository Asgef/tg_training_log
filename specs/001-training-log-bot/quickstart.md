# Quickstart Guide: Local Development Setup

This guide provides instructions for setting up your local development environment for the Telegram Training Log bot.

## Prerequisites

Ensure you have the following installed:
- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Python 3.9+](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv) (for package management)

## 1. Clone the Repository

```bash
git clone <repository_url>
cd tg_training_log
```
Replace `<repository_url>` with the actual URL of your Git repository.

## 2. Environment Configuration

Create a `.env` file in the root of the project by copying `sample.env` (or directly creating it).

```bash
cp sample.env .env
```

Edit the `.env` file and fill in the necessary values:
- `BOT_TOKEN`: Your Telegram Bot API token.
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:password@db:5432/training_log_db`).
- `GOOGLE_SERVICE_ACCOUNT_FILE`: Path to your Google Service Account JSON key file.

## 3. Database Setup with Docker Compose

We will use Docker Compose to run a PostgreSQL database locally.

```bash
docker-compose up -d db
```
This command starts the PostgreSQL container in detached mode.

## 4. Python Dependencies with `uv`

First, create a virtual environment.

```bash
uv venv
```

Then, activate it.
- On macOS/Linux: `source .venv/bin/activate`
- On Windows: `.venv\Scripts\activate`

Install the dependencies from `requirements.txt`.

```bash
uv pip install -r requirements.txt 
```

## 5. Run Database Migrations (Alembic)

*Note: Migration setup will be defined in a later task.*

```bash
alembic upgrade head
```

## 6. Run the Bot

Once the database is up and dependencies are installed, you can start the bot:

```bash
python -m src.main
```

## 7. Stop Services

To stop the Docker containers:

```bash
docker-compose down
```