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
    WHERE e.employee_name = '{employee_name}'
      AND a.attendance_date = '{attendance_date}'
    ORDER BY a.attendance_date DESC
    LIMIT 100;