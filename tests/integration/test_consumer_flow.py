from unittest.mock import patch, MagicMock
from app.consumer.consumer import validate_schema, normalize_event

@patch("app.consumer.influx_writer.write_event_ingest")
def test_event_processing_flow(mock_write):
    topic = "user-events"
    event = {
        "user_id": 1,
        "email": "a@b.com",
        "status": "ACTIVE",
        "created_at": "2024-01-01T10:00:00+05:30Z",
        "updated_at": "2024-01-01T10:00:00+05:30Z",
    }

    # schema validation
    missing = validate_schema(topic, event)
    assert missing == []

    # normalization
    norm = normalize_event(topic, event)
    assert norm["producer"] == "user-service"

    # simulate write
    mock_write(
        topic=topic,
        event_type=norm["event_name"],
        source_team=norm["source_team"],
        latency_ms=10,
        lag=0,
        ts_ms=123456789,
    )

    mock_write.assert_called_once()