from app.consumer.consumer import normalize_event

def test_user_event_normalization():
    result = normalize_event("user-events", {})
    assert result["event_name"] == "user_event"
    assert result["producer"] == "user-service"


def test_order_event_normalization():
    value = {"status": "SHIPPED"}
    result = normalize_event("order-events", value)
    assert result["event_name"] == "order_shipped"
    assert result["producer"] == "order-service"


def test_notification_event_normalization():
    value = {"event_name": "notification_sent", "producer": "notification-service"}
    result = normalize_event("notification-events", value)
    assert result["event_name"] == "notification_sent"