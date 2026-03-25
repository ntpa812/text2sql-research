SELECT SUM(amount_transfer) AS total_amount
    FROM transaction
    WHERE YEAR(trans_time) = YEAR(CURRENT_DATE())
      AND MONTH(trans_time) = 3
      AND trans_status = 'S'
    LIMIT 100;