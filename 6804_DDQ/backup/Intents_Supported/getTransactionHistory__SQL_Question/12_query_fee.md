# SQL Query: Tra cứu phí giao dịch

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, trans_name,
       from_account_no, to_account_no,
       amount_transfer, amount_currency,
       fee_amount, fee_currency, fee_ind,
       commission_amount, commission_currency,
       trans_status, trans_desc
FROM transaction 
WHERE (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
  AND fee_amount > 0
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch có phí trong tháng này
2. Cho tôi danh sách phí giao dịch đã trả
3. Tìm các giao dịch bị tính phí
4. Liệt kê phí chuyển khoản đã thanh toán
5. Tra cứu tổng phí giao dịch trong tháng
6. Cho biết giao dịch nào có phí cao nhất
7. Xem các khoản phí đã bị trừ
8. Tìm phí chuyển tiền liên ngân hàng
9. Liệt kê các giao dịch miễn phí
10. Tra cứu phí dịch vụ ngân hàng
11. Cho xem tổng tiền phí đã chi trong năm
12. Tìm các giao dịch có phí trên 10.000đ
13. Xem danh sách phí giao dịch ATM
14. Liệt kê phí rút tiền đã trả
15. Tra cứu phí thanh toán hóa đơn
16. Cho biết phí SMS Banking trong tháng
17. Tìm các khoản phí duy trì tài khoản
18. Xem phí chuyển tiền nhanh 24/7
19. Liệt kê phí giao dịch quốc tế
20. Tra cứu tổng phí dịch vụ từ đầu năm
