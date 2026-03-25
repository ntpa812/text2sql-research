SELECT
    e.employee_id,
    e.employee_name,
    d.department_name,
    e.job_title,
    e.employment_status,
    e.hire_date
FROM employee e
JOIN department d ON e.department_id = d.department_id
WHERE e.hire_date BETWEEN '{start_date}' AND '{end_date}'
ORDER BY e.hire_date DESC
LIMIT 100;
