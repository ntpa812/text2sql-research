SELECT SUM(lb.remaining_days) as total_remaining_days
            FROM leave_balance lb
            JOIN employee e ON lb.employee_id = e.employee_id
            WHERE e.employee_name = 'Nguyễn Văn An'