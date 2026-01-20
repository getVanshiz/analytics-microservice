
scalar(rate(analytics_events_published_total[5m]))
/
scalar(sum(rate(kafka_messages_consumed_total[5m])))
