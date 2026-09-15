# SteamStats

Веб-приложение для просмотра статистики Steam-профилей: игры, время в игре,
достижения — по SteamID64 или vanity-имени, без обязательной авторизации.
Отдельно — глобальный топ игр по онлайну и поиск статистики любой игры
(SteamSPY), не привязанный к конкретному профилю.

Состоит из четырёх частей, поднимаемых одним `docker compose up`:

- **`backend/`** — FastAPI + PostgreSQL. Резолвит SteamID/vanity, тянет данные
  из Steam Web API, кеширует их в БД (TTL 1 час), отвечает за авторизацию
  через Steam OpenID.
- **`steamspy-service/`** — независимый сервис (свой код, своя БД) поверх
  SteamSPY API: онлайн игр, владельцы, рейтинг обзоров. Никак не связан с
  `backend/` — общих таблиц и общего кода нет.
- **`frontend/`** — React + Vite. Может работать как против реальных
  бэкендов, так и полностью на локальных фикстурах (`frontend/src/data/*.json`),
  если бэкенды не поднялись.
- **`nginx/`** — reverse proxy, объединяющий всё под одним портом (`:8000`):
  `/api/games/` → steamspy-service, остальной `/api/` и `/auth/` → backend,
  всё прочее → фронт.

Полный контракт эндпоинтов и форм ответов — в [`API_CONTRACT.md`](./API_CONTRACT.md).

## Стек

| | |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2.0 (async) + `asyncpg`, PostgreSQL, httpx |
| steamspy-service | Python, FastAPI, SQLAlchemy 2.0 (async) + `asyncpg`, PostgreSQL, httpx |
| Frontend | React 19, Vite, react-router-dom |
| Инфра | Docker Compose (5 сервисов + 2 БД), nginx |
| Линтеры | Ruff (backend), Oxlint (frontend) |

## Быстрый старт

Нужны `.env`-файлы (в `.gitignore`, ни с кем не делятся):

`backend/.env`:
```env
NODE_ENV=development
PORT=8080
APP_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8000

DB_HOST=127.0.0.1
DB_PORT=5555
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
POSTGRES_USER=...       # то же значение, что DB_USER — под именем, которого
POSTGRES_PASSWORD=...   # ждёт образ postgres для самого контейнера
POSTGRES_DB=...         # (см. комментарий в файле)

STEAM_API_KEY=...
```
`STEAM_API_KEY` — на https://steamcommunity.com/dev/apikey, один ключ на всё
приложение (не на пользователя).

`steamspy-service/.env`:
```env
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
DB_HOST=localhost
DB_PORT=5433
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
```

`frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
```
(пусто/не задано = фронт работает на фикстурах).

Дальше — одна команда из корня:
```bash
docker compose up -d --build
```

Поднимутся: `postgres` (backend), `steamspy_postgres`, `backend`, `steamspy_service`,
`frontend` (Vite dev-сервер с hot-reload, код смонтирован с хоста — правки
на диске сразу подхватываются), `nginx`.

Сайт: **http://localhost:8000**. Прямые порты сервисов (`:8080`, `:8081`,
`:5173`, `:5432`/`:5555`, `:5433`) тоже наружу — для отладки и `psql`, но
обычный вход в приложение — только через `:8000`, иначе браузер увидит два
разных origin и часть запросов (CORS) отвалится.

При первом запуске таблицы нужно создать вручную (миграций через Alembic
нет — `schema.sql` в каждом сервисе — справочный файл под структуру):
```bash
docker exec -i steam_stats psql -U <DB_USER> -d <DB_NAME> < backend/src/db/schema.sql
docker exec -i steamspy_db psql -U <DB_USER> -d <DB_NAME> < steamspy-service/src/db/schema.sql
```

## Линтинг

```bash
docker compose exec backend ruff check .
cd frontend && npm run lint
```

## Структура backend

```
backend/src/
├── api/
│   ├── routers.py        # профиль/библиотека: парсинг входа, вызов сервисов, коды ответов
│   └── auth_routers.py   # Steam OpenID логин/логаут/me
├── services/
│   ├── steam_client.py   # обёртки над Steam Web API
│   ├── cache.py          # TTL-логика (протухание кэша)
│   ├── profile.py        # оркестрация профиля
│   ├── library.py        # оркестрация библиотеки игр/достижений
│   └── auth.py           # find-or-create user, сессии
├── db/
│   ├── connection.py      # async-движок SQLAlchemy, сессии
│   ├── models.py          # ORM-модели
│   ├── queries.py         # запросы к БД
│   └── schema.sql
└── schemas/schemas.py     # Pydantic-модели ответов
```

## Структура steamspy-service

```
steamspy-service/src/
├── api/routers.py         # /api/games/search, /top, /{app_id}
├── services/
│   ├── steamspy_client.py # обёртки над SteamSPY API
│   ├── steam_search.py    # поиск игры по названию (Steam store search, не SteamSPY)
│   ├── cache.py            # TTL 24ч — SteamSPY сам обновляется не чаще раза в сутки
│   └── stats.py            # оркестрация + парсинг диапазона owners
├── db/{connection,models,queries}.py, schema.sql
└── schemas/schemas.py
```
