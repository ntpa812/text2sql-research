SELECT trans_id, trans_time, amount_transfer, from_account_no, to_account_no
    FROM transaction
    WHERE trans_time >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
      AND trans_time < DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
      AND (category_code LIKE 'TRANSFER_%' OR category_code = 'REQUEST_TRANSFER')
    LIMIT 100;