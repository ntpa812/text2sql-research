SELECT SUM(amount_transfer) AS total_amount
FROM transaction
WHERE trans_time >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY) AND amount_transfer > 2000000;