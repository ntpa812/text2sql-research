SELECT
    e.employee_id,
    e.employee_name,
    d.department_name,
    e.job_title,
    e.employment_status,
    e.hire_date
FROM employee e
JOIN department d ON e.department_id = d.department_id
WHERE e.job_title LIKE '%{job_title}%'
ORDER BY d.department_name, e.employee_name ASC
LIMIT 100;
