SELECT 
  SUM(t.amount_transfer) AS total_amount
FROM transaction t
WHERE t.trans_time >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
ORDER BY t.trans_time DESC
LIMIT 100;