from datetime import datetime, timedelta, timezone

TTL = timedelta(hours=1)


def is_stale(last_fetched_at: datetime) -> bool:
    return datetime.now(timezone.utc) - last_fetched_at > TTL
