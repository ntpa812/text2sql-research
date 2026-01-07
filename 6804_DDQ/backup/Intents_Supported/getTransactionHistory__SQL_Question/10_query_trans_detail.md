# SQL Query: Tra cứu chi tiết một giao dịch cụ thể

## SQL Template
```sql
SELECT trans_id, trans_code, trans_time, trans_type, trans_name,
       from_account_no, from_account_fullname, from_account_branch,
       to_account_no, to_account_fullname, to_account_branch,
       amount_transfer, amount_currency, fee_amount, fee_currency,
       trans_ref_no, core_ref_no, trans_status, response_status,
       trans_desc, to_message, request_channel,
       request_time, response_time, finish_time
FROM transaction 
WHERE trans_id = '{trans_id}'
   OR trans_ref_no = '{trans_ref_no}';
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem chi tiết giao dịch có mã số 123456789
2. Cho tôi thông tin giao dịch có mã tham chiếu ABC123
3. Tra cứu chi tiết giao dịch số 987654321
4. Tìm thông tin về giao dịch có ID 456789123
5. Liệt kê chi tiết của giao dịch mã GD123456
6. Cho biết thông tin giao dịch có số tham chiếu REF001
7. Xem nội dung giao dịch có mã 111222333
8. Tra cứu giao dịch theo mã tham chiếu TRN20241217001
9. Tìm chi tiết giao dịch có trans_id 789456123
10. Cho xem thông tin đầy đủ của giao dịch số 321654987
11. Kiểm tra trạng thái giao dịch có mã ABC789
12. Xem phí của giao dịch có mã số 555666777
13. Tra cứu thời gian thực hiện giao dịch 123123123
14. Cho biết người nhận của giao dịch có mã REF999
15. Tìm số tiền của giao dịch có ID 888777666
16. Xem kênh thực hiện giao dịch có mã 444555666
17. Tra soát giao dịch có số tham chiếu TRANS001
18. Kiểm tra chi tiết giao dịch mã giao dịch GD789
19. Cho tôi xem toàn bộ thông tin giao dịch số 999888777
20. Tra cứu lý do thất bại của giao dịch có mã ERR123
