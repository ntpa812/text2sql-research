SELECT COUNT(*) 
FROM transaction 
WHERE trans_time >= DATE_SUB(CURDATE(), INTERVAL 0 DAY) 
AND category_code LIKE 'TRANSFER_%' OR category_code = 'REQUEST_TRANSFER';