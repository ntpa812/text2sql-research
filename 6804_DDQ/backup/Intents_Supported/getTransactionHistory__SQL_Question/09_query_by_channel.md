# SQL Query: Tra cứu giao dịch theo kênh giao dịch

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, 
       from_account_no, to_account_no,
       amount_transfer, amount_currency,
       request_channel, source_type, app_version,
       trans_status, trans_desc
FROM transaction 
WHERE (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
  AND request_channel = '{channel}'
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch thực hiện qua Mobile Banking
2. Cho tôi danh sách giao dịch qua Internet Banking
3. Tìm giao dịch được thực hiện tại quầy
4. Liệt kê các giao dịch qua ATM
5. Tra cứu giao dịch thực hiện qua ứng dụng điện thoại
6. Cho biết giao dịch nào thực hiện qua POS
7. Xem các giao dịch qua kênh online
8. Tìm giao dịch thực hiện qua SMS Banking
9. Liệt kê giao dịch qua QR Pay
10. Tra cứu các giao dịch thực hiện trực tiếp tại chi nhánh
11. Cho xem lịch sử giao dịch qua app ngân hàng
12. Tìm các giao dịch thực hiện qua website
13. Xem danh sách giao dịch qua máy CDM
14. Liệt kê giao dịch thanh toán qua thẻ
15. Tra cứu giao dịch qua kênh NAPAS
16. Cho biết giao dịch nào từ Apple Pay
17. Tìm các giao dịch qua Samsung Pay
18. Xem giao dịch thực hiện qua Google Pay
19. Liệt kê giao dịch qua VNPay
20. Tra cứu các giao dịch qua MoMo
