# JSON Event Schemas

## User Events (`user-events`)

```json
{
  "user_id": 123,
  "email": "user@example.com",
  "status": "ACTIVE",
  "created_at": "2024-01-01T10:00:00+05:30Z",
  "updated_at": "2024-01-01T10:00:00+05:30Z"
}
```
Required fields:
- user_id
- email
- status
- created_at
- updated_at

## Order Events (`order-events`)

```Json
{
  "id": "uuid",
  "user_id": "user123",
  "item": "laptop",
  "quantity": 2,
  "status": "SHIPPED",
  "created_at": "2024-01-01T10:00:00+05:30Z",
  "updated_at": "2024-01-01T10:00:00+05:30Z"
}
```

Required fields:
- id
- user_id
- item
- quantity
- status
- created_at
- update_at


Notification Events (`notification-events`)

```Json
{
  "event_name": "notification_sent",
  "event_version": "1.0",
  "event_id": "uuid",
  "occurred_at": "2024-01-01 10:00:00 IST",
  "producer": "notification-service",
  "data": {
    "user_id": "user123",
    "order_id": "order456",
    "channel": "EMAIL",
    "status": "SENT"
  }
}
```

Required fields:
- event_name
- event_version
- event_id
- occured_at
- producer
- data

## Validation Behavior
- Missing fields are logged
- Validation failures increment metrics
- Invalid events do not crash the service