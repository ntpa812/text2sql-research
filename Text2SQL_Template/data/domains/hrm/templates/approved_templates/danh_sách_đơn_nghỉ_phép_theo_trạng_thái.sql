SELECT COUNT(*) AS pending_count
FROM leave_request lr
WHERE lr.status = '{status}' AND lr.start_date >= CURRENT_DATE;