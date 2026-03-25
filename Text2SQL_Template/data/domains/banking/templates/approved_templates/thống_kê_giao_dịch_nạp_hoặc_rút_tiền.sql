SELECT 
  COUNT(*)            AS total_transactions,
  SUM(amount_transfer) AS total_amount
FROM transaction
WHERE trans_type = 'DEPOSIT'
  AND EXTRACT(MONTH FROM transaction.trans_time) = MONTH(CURRENT_DATE)
  AND EXTRACT(YEAR FROM transaction.trans_time) = YEAR(CURRENT_DATE);