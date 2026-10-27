# SteamStats

![CI](https://github.com/Thief1232/SteamStats/actions/workflows/ci.yml/badge.svg)

Веб-приложение для просмотра статистики Steam-профилей: игры, время в игре,
достижения — по SteamID64 или vanity-имени, без обязательной авторизации.
Отдельно — глобальный топ игр по онлайну и поиск статистики любой игры
(SteamSPY), не привязанный к конкретному профилю.

## Состав

- **`backend/`** — FastAPI + PostgreSQL. Профили и библиотеки из Steam Web API
  с кэшем в БД, вход через Steam OpenID.
- **`steamspy-service/`** — независимый сервис со своей БД поверх SteamSPY API:
  онлайн игр, владельцы, рейтинг обзоров.
- **`frontend/`** — React + Vite.
- **`nginx/`** — reverse proxy, объединяет всё под одним портом.

## Стек

Python, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, httpx · React 19, Vite ·
Docker Compose, nginx · Ruff, Oxlint, pytest
