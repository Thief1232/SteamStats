-- Minimal schema for /api/users/{lookup} and /api/users/{steam_id}/library.
-- Achievements are stored as an aggregate (unlocked/total) directly in
-- owned_games, which is how the GetPlayerAchievements aggregation returns them
-- and how the fixture (frontend/src/data/library.json) looks. A normalized
-- per-achievement table only makes sense once the UI needs to show which
-- specific achievements are missing, not just the percentage.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Steam profile. Exists independently of users — created on the first public
-- view (GET /api/users/{lookup}), no registration needed. user_id is set only
-- when the owner actually signs in through Steam.
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

-- Game catalog. Shared by everyone, independent of who played the games.
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    icon_url TEXT
);

-- Library of a specific steam_id. TTL cache: last_fetched_at says whether
-- the Steam API should be queried again.
CREATE TABLE IF NOT EXISTS owned_games (
    steam_id BIGINT NOT NULL REFERENCES steam_accounts(steam_id),
    app_id INTEGER NOT NULL REFERENCES games(app_id),
    playtime_minutes INTEGER NOT NULL DEFAULT 0,
    playtime_2weeks_minutes INTEGER NOT NULL DEFAULT 0,
    last_played TIMESTAMPTZ,
    achievements_unlocked INTEGER,
    achievements_total INTEGER,
    achievements_fetched_at TIMESTAMPTZ,
    last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (steam_id, app_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);
-- For databases created before the achievements TTL existed.
ALTER TABLE owned_games ADD COLUMN IF NOT EXISTS achievements_fetched_at TIMESTAMPTZ;
