SELECT
    a.employee_id,
    e.employee_name,
    d.department_name,
    strftime('%Y-%m', a.attendance_date)                           AS month,
    SUM(CASE WHEN a.status = 'PRESENT'  THEN 1 ELSE 0 END)        AS present_days,
    SUM(CASE WHEN a.status = 'LATE'     THEN 1 ELSE 0 END)        AS late_days,
    SUM(CASE WHEN a.status = 'REMOTE'   THEN 1 ELSE 0 END)        AS remote_days,
    SUM(CASE WHEN a.status = 'ABSENT'   THEN 1 ELSE 0 END)        AS absent_days,
    SUM(CASE WHEN a.status = 'ON_LEAVE' THEN 1 ELSE 0 END)        AS on_leave_days,
    COUNT(*)                                                       AS total_working_days
FROM attendance a
JOIN employee e ON a.employee_id = e.employee_id
JOIN department d ON e.department_id = d.department_id
WHERE strftime('%Y-%m', a.attendance_date) = '{year_month}'
GROUP BY a.employee_id, e.employee_name, d.department_name, strftime('%Y-%m', a.attendance_date)
ORDER BY d.department_name, e.employee_name
LIMIT 100;
