SELECT
    a.attendance_id,
    a.employee_id,
    e.employee_name,
    a.attendance_date,
    a.check_in_time,
    a.check_out_time,
    a.status
FROM attendance a
JOIN employee e ON a.employee_id = e.employee_id
WHERE a.employee_id = '{employee_id}'
  AND a.attendance_date BETWEEN '{start_date}' AND '{end_date}'
ORDER BY a.attendance_date DESC
LIMIT 100;
