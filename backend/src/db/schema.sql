-- Минимальная схема под то, что уже нужно для /api/users/{lookup} и
-- /api/users/{steam_id}/library (см. /API_CONTRACT.md). Достижения хранятся
-- как агрегат (unlocked/total) прямо в owned_games, потому что именно в таком
-- виде их отдаёт GetPlayerAchievements-агрегация и именно так выглядит
-- фикстура (frontend/src/data/library.json) — отдельная нормализованная
-- таблица под список конкретных ачивок имеет смысл только когда реально
-- понадобится показывать, какие именно ачивки не взяты, а не только процент.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Профиль Steam. Существует независимо от users — заводится при первом же
-- публичном просмотре (GET /api/users/{lookup}), без всякой регистрации.
-- user_id проставляется только когда владелец реально логинится через Steam.
CREATE TABLE IF NOT EXISTS steam_accounts (
    steam_id BIGINT PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    persona_name TEXT NOT NULL,
    avatar_url TEXT,
    profile_url TEXT,
    account_created TIMESTAMPTZ,
    visibility TEXT NOT NULL DEFAULT 'public',
    linked_at TIMESTAMPTZ,
    last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Каталог игр. Общий для всех — не зависит от того, кто их наигрывал.
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    icon_url TEXT
);

-- Библиотека конкретного steam_id. TTL-кэш: last_fetched_at говорит,
-- пора ли перезапрашивать Steam API (см. API_CONTRACT.md, "Кэш с TTL").
CREATE TABLE IF NOT EXISTS owned_games (
    steam_id BIGINT NOT NULL REFERENCES steam_accounts(steam_id),
    app_id INTEGER NOT NULL REFERENCES games(app_id),
    playtime_minutes INTEGER NOT NULL DEFAULT 0,
    playtime_2weeks_minutes INTEGER NOT NULL DEFAULT 0,
    last_played TIMESTAMPTZ,
    achievements_unlocked INTEGER,
    achievements_total INTEGER,
    last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (steam_id, app_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);