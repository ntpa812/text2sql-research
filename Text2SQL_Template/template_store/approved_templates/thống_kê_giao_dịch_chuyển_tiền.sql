SELECT SUM(amount_transfer) AS total_transferred
FROM transaction
WHERE DATE(trans_time) = CURDATE()
  AND trans_status = 'S';