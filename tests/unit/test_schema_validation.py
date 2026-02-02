from app.consumer.consumer import validate_schema

def test_user_event_valid():
    event = {
        "user_id": 1,
        "email": "test@example.com",
        "status": "ACTIVE",
        "created_at": "2024-01-01T10:00:00+05:30Z",
        "updated_at": "2024-01-01T10:00:00+05:30Z",
    }
    assert validate_schema("user-events", event) == []


def test_user_event_missing_fields():
    event = {
        "user_id": 1,
        "email": "test@example.com",
    }
    missing = validate_schema("user-events", event)
    assert "status" in missing
    assert "created_at" in missing


def test_unknown_topic():
    event = {"a": 1}
    assert validate_schema("unknown-topic", event) == []