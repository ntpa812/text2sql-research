SELECT
    a.employee_id,
    e.employee_name,
    d.department_name,
    a.attendance_date,
    a.status
FROM attendance a
JOIN employee e ON a.employee_id = e.employee_id
JOIN department d ON e.department_id = d.department_id
WHERE a.status = 'ABSENT'
  AND a.attendance_date = '{attendance_date}'
ORDER BY d.department_name, e.employee_name ASC
LIMIT 100;
