SELECT trans_id, trans_time, trans_type, trans_name, from_account_no, to_account_no, amount_transfer, amount_currency, trans_status, trans_desc
FROM transaction
WHERE (category_code LIKE 'TRANSFER_%' OR category_code = 'REQUEST_TRANSFER')
AND (from_account_no = '{account_number}')
AND (to_account_no = '{to_account_number}')
ORDER BY trans_time DESC
LIMIT 100;