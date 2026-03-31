SELECT COUNT(*) AS pending_count
FROM leave_request lr
WHERE lr.status = 'pending' AND lr.start_date >= CURRENT_DATE;