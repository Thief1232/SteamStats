# SteamStats

Веб-приложение для просмотра статистики Steam-профилей: игры, время в игре,
достижения — по SteamID64 или vanity-имени, без обязательной авторизации.

Состоит из двух частей:

- **`backend/`** — FastAPI + PostgreSQL. Резолвит SteamID/vanity, тянет данные
  из Steam Web API, кеширует их в БД (TTL 1 час) и отдаёт фронту.
- **`frontend/`** — React + Vite. Может работать как против реального бэкенда,
  так и полностью на локальных фикстурах (`frontend/src/data/*.json`), если
  бэкенд не поднят — удобно для чистой фронтенд-разработки.

Полный контракт эндпоинтов и форм ответов — в [`API_CONTRACT.md`](./API_CONTRACT.md).

## Стек

| | |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2.0 (async) + `asyncpg`, PostgreSQL, httpx |
| Frontend | React 19, Vite, react-router-dom |
| Линтеры | Ruff (backend), Oxlint (frontend) |

## Быстрый старт

### 1. Backend

Поднять базу данных (Docker):

```bash
cd backend
docker compose up -d
```

Создать `.env` в `backend/` (файл в `.gitignore`, ни с кем не делится) со
следующими переменными:

```env
NODE_ENV=development
PORT=8080
APP_URL=http://localhost:8080

DB_HOST=localhost
DB_PORT=5432
DB_USER=...
DB_PASSWORD=...
DB_NAME=...

STEAM_API_KEY=...
```

`STEAM_API_KEY` получается на https://steamcommunity.com/dev/apikey — один
ключ на всё приложение (не на пользователя).

Установить зависимости и запустить сервер:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn src.main:app --reload --port 8080
```

Бэкенд поднимется на `http://localhost:8080`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

По умолчанию фронт работает на фикстурах. Чтобы переключить его на реальный
бэкенд, задайте в `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8080
```

(см. `frontend/.env.example`) — код страниц менять не нужно, переключение
происходит в `src/api/client.js`.

## Линтинг

```bash
cd backend && .venv/bin/ruff check .
cd frontend && npm run lint
```

## Структура backend

```
backend/src/
├── api/routers.py       # HTTP-слой: парсинг входа, вызов сервисов, коды ответов
├── services/
│   ├── steam_client.py  # обёртки над Steam Web API
│   ├── cache.py         # TTL-логика (protuxание кэша)
│   ├── profile.py       # оркестрация профиля
│   └── library.py       # оркестрация библиотеки игр/достижений
├── db/
│   ├── connection.py     # async-движок SQLAlchemy, сессии
│   ├── models.py         # ORM-модели
│   ├── queries.py        # запросы к БД
│   └── schema.sql/seed.sql
└── schemas/schemas.py    # Pydantic-модели ответов
```
