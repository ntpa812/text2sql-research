SELECT COUNT(*) 
FROM transaction 
WHERE EXTRACT(MONTH FROM transaction.trans_time) = 6 AND trans_type = 'DIMENSION' AND channel_receiver = 'DIMENSION';