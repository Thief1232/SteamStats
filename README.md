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
- **`nginx/`** — reverse proxy that serves everything under a single port.

## Stack

Python, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, httpx · React 19, Vite ·
Docker Compose, nginx · Ruff, Oxlint, pytest
