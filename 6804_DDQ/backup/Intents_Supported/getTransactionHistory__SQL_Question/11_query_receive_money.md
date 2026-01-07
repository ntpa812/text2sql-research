# SQL Query: Tra cứu giao dịch nhận tiền

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, 
       from_account_no, from_account_fullname, 
       to_account_no, to_account_fullname,
       amount_transfer, amount_currency,
       trans_status, trans_desc, from_message
FROM transaction 
WHERE to_account_no = '{account_number}'
  AND trans_status = 'S'
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch nhận tiền vào tài khoản
2. Cho tôi danh sách tiền đã nhận được
3. Tìm các lần được chuyển tiền vào
4. Liệt kê giao dịch tiền vào trong tháng
5. Tra cứu ai đã chuyển tiền cho tôi
6. Cho biết các khoản tiền đã nhận được hôm nay
7. Xem lịch sử tiền ghi có vào tài khoản
8. Tìm giao dịch nhận tiền từ Nguyễn Văn A
9. Liệt kê các khoản tiền nhận từ tài khoản 0123456789
10. Tra cứu số tiền đã nhận trong tuần này
11. Cho xem những ai đã chuyển tiền đến tài khoản của tôi
12. Tìm các giao dịch nhận tiền trên 5 triệu
13. Xem danh sách người gửi tiền thường xuyên
14. Liệt kê tiền nhận từ lương hàng tháng
15. Tra cứu giao dịch nhận tiền từ ngân hàng khác
16. Cho biết tổng số tiền đã nhận trong tháng
17. Tìm giao dịch nhận tiền có nội dung "lương"
18. Xem các khoản tiền nhận từ công ty
19. Liệt kê giao dịch nhận tiền cùng ngân hàng
20. Tra cứu các lần nhận tiền trong 7 ngày qua
