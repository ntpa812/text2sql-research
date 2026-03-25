SELECT SUM(amount_transfer) AS total_amount
FROM transaction
WHERE MONTH(trans_time) = 1
LIMIT 100;