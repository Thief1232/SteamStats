from datetime import datetime, timedelta, timezone

TTL = timedelta(hours=24)


def is_stale(last_fetched_at: datetime) -> bool:
    return datetime.now(timezone.utc) - last_fetched_at > TTL

