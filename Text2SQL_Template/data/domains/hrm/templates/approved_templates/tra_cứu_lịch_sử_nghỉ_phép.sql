SELECT lr.request_id, lr.employee_id, e.employee_name, lt.leave_type_name,
       lr.start_date, lr.end_date, lr.total_days, lr.reason, lr.status, lr.created_at
FROM leave_request lr
JOIN employee e ON lr.employee_id = e.employee_id
JOIN leave_type lt ON lr.leave_type_id = lt.leave_type_id
WHERE lr.employee_id = '{employee_id}'
ORDER BY lr.created_at DESC
LIMIT 100;
