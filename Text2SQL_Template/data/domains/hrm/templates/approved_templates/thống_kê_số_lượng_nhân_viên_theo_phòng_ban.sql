SELECT d.department_id, d.department_name, COUNT(e.employee_id) as count
    FROM department d
    LEFT JOIN employee e ON d.department_id = e.department_id
    GROUP BY d.department_id, d.department_name
    ORDER BY count DESC
    LIMIT 100;