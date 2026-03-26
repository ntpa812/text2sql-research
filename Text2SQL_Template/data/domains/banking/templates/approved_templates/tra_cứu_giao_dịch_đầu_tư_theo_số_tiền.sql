SELECT trans_id, trans_time, trans_type, trans_name,
           from_account_no, to_account_no,
           amount_transfer, amount_currency,
           trans_status, trans_desc
    FROM transaction
    WHERE trans_time BETWEEN '2025-01-01' AND '2025-03-31'
      AND amount_transfer BETWEEN 5000000 AND 20000000
    ORDER BY trans_time DESC
    LIMIT 100;