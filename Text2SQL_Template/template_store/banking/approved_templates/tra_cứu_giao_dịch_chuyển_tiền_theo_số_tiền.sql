SELECT COUNT(*) AS total_transactions
FROM transaction
WHERE trans_time >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
  AND trans_time < CURDATE();