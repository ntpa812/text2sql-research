SELECT
    e.employee_id,
    e.employee_name,
    d.department_name,
    e.job_title,
    e.employment_status,
    e.hire_date,
    e.email,
    e.phone
FROM employee e
JOIN department d ON e.department_id = d.department_id
WHERE e.employee_id = '{employee_id}'
LIMIT 100;
