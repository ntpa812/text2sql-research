SELECT SUM(t.amount_transfer) AS total_transfer
FROM transaction t
JOIN customer_account c ON t.from_account_no = c.account_no
WHERE c.account_no = '123456789'
AND t.category_code LIKE 'TRANSFER_%'
ORDER BY t.trans_time DESC;