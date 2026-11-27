#!/bin/sh
# Bring the database schema up to date, then start whatever CMD/command says
# (uvicorn in production, uvicorn --reload in local dev). A failed migration
# stops the container instead of starting the app on a stale schema.
set -e
alembic upgrade head
exec "$@"
