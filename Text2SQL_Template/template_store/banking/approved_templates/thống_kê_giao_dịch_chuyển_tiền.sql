SELECT SUM(amount_transfer) AS total_received
FROM transaction
WHERE YEAR(trans_time) = YEAR(CURRENT_DATE())
  AND MONTH(trans_time) = 4
  AND trans_status = 'S'
LIMIT 100;