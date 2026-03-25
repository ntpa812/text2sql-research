SELECT SUM(amount_transfer) AS total_transfer_amount
FROM transaction
WHERE MONTH(trans_time) = 1;