SELECT SUM(t.amount_transfer) AS total_transfer
FROM transaction t
JOIN customer_account c ON t.from_account_no = c.account_no
WHERE c.account_no = '888999'
AND t.trans_time >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
AND t.category_code LIKE 'TRANSFER_%'
ORDER BY t.trans_time DESC;