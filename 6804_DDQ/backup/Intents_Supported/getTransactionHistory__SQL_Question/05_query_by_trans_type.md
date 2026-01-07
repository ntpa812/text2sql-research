# SQL Query: Tra cứu giao dịch theo loại giao dịch

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, trans_name, from_account_no, to_account_no, 
       amount_transfer, amount_currency, trans_status, trans_desc
FROM transaction 
WHERE trans_type = '{trans_type}'
  AND (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch chuyển tiền trong tài khoản
2. Cho tôi danh sách giao dịch thanh toán
3. Tìm các giao dịch rút tiền
4. Liệt kê giao dịch nạp tiền vào tài khoản
5. Tra cứu các giao dịch chuyển khoản
6. Cho biết các giao dịch mua hàng online
7. Xem giao dịch thanh toán hóa đơn
8. Tìm các giao dịch chuyển tiền nội bộ
9. Liệt kê giao dịch chuyển tiền liên ngân hàng
10. Tra cứu giao dịch thanh toán QR Code
11. Cho xem các giao dịch trả góp
12. Tìm giao dịch mua thẻ điện thoại
13. Xem danh sách giao dịch nạp tiền điện thoại
14. Liệt kê các giao dịch thanh toán tiền điện
15. Tra cứu giao dịch đóng phí bảo hiểm
16. Cho biết các giao dịch chuyển tiền quốc tế
17. Tìm giao dịch thanh toán thẻ tín dụng
18. Xem các giao dịch gửi tiết kiệm
19. Liệt kê giao dịch rút tiết kiệm
20. Tra cứu các giao dịch vay vốn
