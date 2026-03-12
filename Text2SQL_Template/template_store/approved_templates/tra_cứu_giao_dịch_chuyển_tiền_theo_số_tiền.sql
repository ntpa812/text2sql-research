SELECT 
  COUNT(*) AS total_transactions
FROM 
  transaction
WHERE 
  trans_time >= DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY) AND 
  trans_time < DATE_SUB(CURRENT_DATE, INTERVAL 0 DAY)