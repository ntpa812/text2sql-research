SELECT lr.request_id, lr.employee_id, lr.start_date, lr.end_date, lr.total_days, lr.reason, lr.status
FROM leave_request lr
WHERE lr.start_date >= CURRENT_DATE
ORDER BY lr.total_days DESC
LIMIT 100;