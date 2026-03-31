SELECT
    lb.employee_id,
    lb.total_days,
    lb.used_days,
    lb.remaining_days,
    lt.leave_type_name
FROM leave_balance lb
JOIN leave_type lt ON lb.leave_type_id = lt.leave_type_id
WHERE lb.year = CAST(STRFTIME('%Y', CURRENT_DATE) AS INTEGER)
ORDER BY lb.remaining_days DESC
LIMIT 1;