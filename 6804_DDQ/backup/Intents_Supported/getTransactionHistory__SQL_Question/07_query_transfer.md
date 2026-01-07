# SQL Query: Tra cứu giao dịch chuyển tiền

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, 
       from_account_no, from_account_fullname, 
       to_account_no, to_account_fullname,
       amount_transfer, amount_currency, fee_amount,
       trans_status, trans_desc, to_message
FROM transaction 
WHERE from_account_no = '{account_number}'
  AND trans_type IN ('TRANSFER', 'INTERNAL_TRANSFER', 'EXTERNAL_TRANSFER')
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch chuyển tiền đã thực hiện
2. Cho tôi danh sách các lần chuyển khoản
3. Tìm các giao dịch chuyển tiền từ tài khoản của tôi
4. Liệt kê giao dịch chuyển tiền nội bộ
5. Tra cứu lịch sử chuyển khoản liên ngân hàng
6. Cho biết tôi đã chuyển tiền cho ai trong tháng này
7. Xem các giao dịch chuyển tiền trong tuần qua
8. Tìm giao dịch chuyển tiền cho số tài khoản 0123456789
9. Liệt kê các lần chuyển khoản trên 10 triệu đồng
10. Tra cứu giao dịch chuyển tiền cho Nguyễn Văn A
11. Cho xem những ai đã nhận tiền từ tài khoản của tôi
12. Tìm các giao dịch chuyển tiền bị lỗi
13. Xem danh sách người nhận tiền thường xuyên
14. Liệt kê giao dịch chuyển tiền cùng ngân hàng
15. Tra cứu chuyển khoản sang ngân hàng khác
16. Cho biết phí chuyển tiền của các giao dịch
17. Tìm giao dịch chuyển tiền có nội dung "thanh toán"
18. Xem các giao dịch chuyển tiền nhanh 24/7
19. Liệt kê chuyển khoản đã thực hiện hôm nay
20. Tra cứu giao dịch chuyển tiền đang chờ xử lý
