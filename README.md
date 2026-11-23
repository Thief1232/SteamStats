# SteamStats

![CI](https://github.com/Thief1232/SteamStats/actions/workflows/ci.yml/badge.svg)

A web app for browsing Steam profile statistics: games, playtime and
achievements — by SteamID64 or vanity name, no sign-in required. It also has
a global top of games by online players and per-game stats lookup (SteamSPY),
independent of any profile.

## Components

- **`backend/`** — FastAPI + PostgreSQL. Profiles and libraries from the Steam
  Web API cached in the DB, sign-in via Steam OpenID.
- **`steamspy-service/`** — standalone service with its own DB on top of the
  SteamSPY API: online players, owners, review ratio.
- **`frontend/`** — React + Vite.
- **`caddy/`** — reverse proxy that serves everything under a single address
  (and handles HTTPS on the server).

## Running

Locally (code reloads on change, app at http://localhost:8000):

```sh
docker compose up --build
```

On a server (needs `SITE_ADDRESS` in `./.env`, see `.env.example`):

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`docker-compose.yml` holds what both share; `docker-compose.override.yml`
(dev, loaded automatically) and `docker-compose.prod.yml` (server) add the rest.
Database schemas are applied on the first start of an empty volume.

## Stack

Python, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, httpx · React 19, Vite ·
Docker Compose, Caddy · Ruff, Oxlint, pytest
