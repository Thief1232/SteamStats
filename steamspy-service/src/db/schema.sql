CREATE TABLE IF NOT EXISTS game_stats (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    owners_min BIGINT,
    owners_max BIGINT,
    average_playtime_forever INTEGER,
    median_playtime_forever INTEGER,
    ccu INTEGER,
    positive INTEGER,
    negative INTEGER,
    last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);