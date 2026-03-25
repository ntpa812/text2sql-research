SELECT
    d.department_id,
    d.department_name,
    COUNT(CASE WHEN e.employment_status = 'ACTIVE'    THEN 1 END) AS active_count,
    COUNT(CASE WHEN e.employment_status = 'PROBATION' THEN 1 END) AS probation_count,
    COUNT(CASE WHEN e.employment_status = 'SUSPENDED' THEN 1 END) AS suspended_count,
    COUNT(e.employee_id)                                           AS total_count
FROM department d
LEFT JOIN employee e ON d.department_id = e.department_id
GROUP BY d.department_id, d.department_name
ORDER BY total_count DESC
LIMIT 100;
