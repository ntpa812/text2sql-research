SELECT lb.employee_id, e.employee_name, lt.leave_type_name,
       lb.total_days, lb.used_days, lb.remaining_days
FROM leave_balance lb
JOIN employee e ON lb.employee_id = e.employee_id
JOIN leave_type lt ON lb.leave_type_id = lt.leave_type_id
WHERE lb.employee_id = '{employee_id}'
AND lb.year = 2026
ORDER BY lt.leave_type_id
LIMIT 100;
