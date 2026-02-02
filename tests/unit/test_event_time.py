from app.consumer.consumer import parse_event_time_ms

def test_user_event_time():
    event = {
        "created_at": "2024-01-01T10:00:00+05:30Z"
    }
    ts = parse_event_time_ms("user-events", event)
    assert isinstance(ts, int)


def test_notification_event_time():
    event = {
        "occurred_at": "2024-01-01 10:00:00 IST"
    }
    ts = parse_event_time_ms("notification-events", event)
    assert isinstance(ts, int)


def test_missing_time_returns_now():
    ts = parse_event_time_ms("user-events", {})
    assert isinstance(ts, int)