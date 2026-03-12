SELECT 
  *
FROM 
  transaction
WHERE 
  trans_time >= '2024-02-20'
ORDER BY 
  trans_time DESC
LIMIT 100;