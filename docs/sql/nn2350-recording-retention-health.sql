SELECT
  approval_active,
  approval_seconds_left,
  pending_intent_count,
  oldest_pending_seconds,
  deleted_5m,
  audited_deleted_5m,
  due_candidate_count,
  active_legal_hold_count,
  deleted_without_gone_count,
  gone_without_deleted_count,
  warning_pending_over_30m,
  warning_failed_1h
FROM nn2350_monitor_recording_retention_health;
