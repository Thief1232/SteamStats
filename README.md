# SteamStats

![CI](https://github.com/Thief1232/SteamStats/actions/workflows/ci.yml/badge.svg)

A web app for browsing Steam profile statistics: games, playtime and
achievements — by SteamID64 or vanity name, no sign-in required (signing in
through Steam is needed only to load achievements, which costs Steam API calls). It also has
a global top of games by online players and per-game stats lookup (SteamSPY),
independent of any profile.

**Live:** https://steam.thief.beer

## Components

- **`backend/`** — FastAPI + PostgreSQL. Profiles and libraries from the Steam
  Web API cached in the DB, sign-in via Steam OpenID.
- **`steamspy-service/`** — standalone service with its own DB on top of the
  SteamSPY API: online players, owners, review ratio.
- **`frontend/`** — React + Vite.
- **`caddy/`** — reverse proxy that serves everything under a single address
  (on the server, Dokploy's Traefik sits in front of it and handles HTTPS).

## Running

All settings live in one `.env` next to `docker-compose.yml`; `.env.example`
lists and explains every variable.

Locally (code reloads on change, app at http://localhost:8000):

```sh
cp .env.example .env   # then fill in
docker compose up --build
```

`docker-compose.yml` is the production config; `docker-compose.override.yml`
adds the dev bits (bind mounts, reload, local ports) and is loaded automatically
by `docker compose up`. The services read their settings from the environment
compose passes them; they have no `.env` files of their own.

Frontend only, without any backend: `cd frontend && VITE_USE_FIXTURES=true npm run dev`
answers every API call from the fixtures in `src/data/`.

On a server with [Dokploy](https://dokploy.com): create a Docker Compose app from
this repository with Compose Path `./docker-compose.yml`, paste the variables from
`.env.example` (with production values) into the Environment tab, and add the
domain on service `caddy`, port 80, with HTTPS.

## Database changes

Each Python service owns its schema as Alembic migrations (`migrations/versions/`)
and applies them on start (`alembic upgrade head` in `entrypoint.sh`), so a deploy
updates the database by itself. To change the schema, edit `src/db/models.py`, then
generate a migration with the stack running and review it before committing:

```sh
docker compose exec backend alembic revision --autogenerate --rev-id 0002 -m "add something"
```

CI applies the migrations to an empty database and fails if the models and the
migrations disagree (`alembic check`).

## Steam API usage

Steam allows about 100k Web API calls a day per key, and its CDN blocks an IP that
sends bursts. The backend paces its calls (`backend/src/services/steam_client.py`),
pauses for a few minutes when Steam throttles it, and serves cached data meanwhile.
Achievements are fetched only for games played since they were last checked.

## Logs

Both Python services write one line per event to stdout, the same format as
uvicorn's request lines, e.g.
`2026-11-27T14:03:12Z WARNING [src.services.steam_client] Steam throttles us ...`.
On the server they are in Dokploy (the app's Logs tab, per service); locally,
`docker compose logs -f backend`. `LOG_LEVEL` in the environment changes the level.

## Stack

Python, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, httpx · React 19, Vite ·
Docker Compose, Caddy, Alembic · Ruff, Oxlint, pytest
