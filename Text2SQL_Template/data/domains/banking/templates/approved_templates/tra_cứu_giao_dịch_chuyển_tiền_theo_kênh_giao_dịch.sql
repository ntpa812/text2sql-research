SELECT SUM(amount_transfer)
    FROM transaction
    WHERE trans_time >= '2026-03-26' AND trans_time < '2026-03-27'
      AND request_channel = 'INTERNET_BANKING'
      AND trans_type = 'TRANSFER'
    LIMIT 100;