# SQL Query: Tra cứu giao dịch thẻ

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, trans_name,
       from_account_no, card_number,
       amount_transfer, amount_currency,
       partner_code, request_channel,
       trans_status, trans_desc
FROM transaction 
WHERE from_account_no = '{account_number}'
  AND card_number IS NOT NULL
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch thẻ trong tháng này
2. Cho tôi danh sách giao dịch bằng thẻ ATM
3. Tìm các lần quẹt thẻ tín dụng
4. Liệt kê giao dịch thanh toán bằng thẻ
5. Tra cứu lịch sử rút tiền ATM
6. Cho biết các giao dịch POS bằng thẻ
7. Xem giao dịch thẻ ghi nợ trong tuần
8. Tìm các giao dịch thanh toán thẻ Visa
9. Liệt kê giao dịch thẻ MasterCard
10. Tra cứu các lần thanh toán online bằng thẻ
11. Cho xem lịch sử giao dịch thẻ nội địa
12. Tìm giao dịch thẻ quốc tế
13. Xem danh sách giao dịch qua thẻ chip
14. Liệt kê các lần rút tiền từ thẻ
15. Tra cứu giao dịch thanh toán không tiếp xúc
16. Cho biết giao dịch thẻ có giá trị cao nhất
17. Tìm các giao dịch thẻ bị từ chối
18. Xem lịch sử thanh toán thẻ tại cửa hàng
19. Liệt kê giao dịch thẻ phát sinh hôm nay
20. Tra cứu tổng chi tiêu qua thẻ trong tháng
