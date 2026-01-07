# SQL Query: Tra cứu lịch sử giao dịch theo số tài khoản

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, from_account_no, to_account_no, 
       amount_transfer, amount_currency, trans_status, trans_desc
FROM transaction 
WHERE from_account_no = '{account_number}' 
   OR to_account_no = '{account_number}'
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Cho tôi xem lịch sử giao dịch của tài khoản 0123456789
2. Tôi muốn tra cứu các giao dịch của số tài khoản 0123456789
3. Liệt kê tất cả giao dịch liên quan đến tài khoản 0123456789
4. Xem chi tiết các giao dịch từ tài khoản số 0123456789
5. Tài khoản 0123456789 có những giao dịch nào?
6. Kiểm tra lịch sử giao dịch cho tài khoản 0123456789
7. Hiển thị danh sách giao dịch của tài khoản 0123456789
8. Tìm các giao dịch đã thực hiện trên tài khoản 0123456789
9. Tra cứu thông tin giao dịch của STK 0123456789
10. Cho biết các giao dịch phát sinh trên tài khoản 0123456789
11. Lấy danh sách giao dịch của số tài khoản 0123456789
12. Xem sao kê giao dịch tài khoản 0123456789
13. Cung cấp lịch sử giao dịch của TK 0123456789
14. Tài khoản số 0123456789 đã giao dịch những gì?
15. Tôi cần kiểm tra các giao dịch của tài khoản 0123456789
16. Cho xem các giao dịch đi và đến tài khoản 0123456789
17. Tra soát giao dịch của số tài khoản 0123456789
18. Lịch sử giao dịch của STK 0123456789 như thế nào?
19. Cho tôi biết tài khoản 0123456789 có giao dịch gì không?
20. Liệt kê các lần giao dịch của tài khoản 0123456789
