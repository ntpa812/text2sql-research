SELECT SUM(amount_transfer)
            FROM transaction
            WHERE from_account_no = '789'
              AND (category_code LIKE 'TRANSFER_%' OR category_code = 'REQUEST_TRANSFER')
              AND MONTH(trans_time) BETWEEN 1 AND 3