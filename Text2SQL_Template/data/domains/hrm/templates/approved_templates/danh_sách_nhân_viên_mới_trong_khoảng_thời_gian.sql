SELECT
    e.employee_id,
    e.employee_name,
    e.department_id,
    e.job_title,
    e.employment_status,
    e.hire_date
FROM employee e
WHERE e.hire_date BETWEEN '{start_date}' AND '{end_date}'
ORDER BY e.hire_date DESC
LIMIT 100;