SELECT COUNT(*) 
FROM transaction 
WHERE EXTRACT(MONTH FROM transaction.trans_time) = MONTH(CURRENT_DATE) AND trans_type = 'DIMENSION' AND channel_receiver = 'DIMENSION' 
LIMIT 100;