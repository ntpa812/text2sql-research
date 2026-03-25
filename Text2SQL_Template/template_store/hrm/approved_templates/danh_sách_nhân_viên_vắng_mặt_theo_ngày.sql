SELECT
    e.employee_id,
    e.employee_name,
    d.department_name,
    e.job_title,
    a.status
FROM attendance a
JOIN employee e ON a.employee_id = e.employee_id
JOIN department d ON e.department_id = d.department_id
WHERE a.attendance_date = '{attendance_date}'
  AND a.status IN ('ABSENT', 'ON_LEAVE')
ORDER BY d.department_name, e.employee_name
LIMIT 100;
