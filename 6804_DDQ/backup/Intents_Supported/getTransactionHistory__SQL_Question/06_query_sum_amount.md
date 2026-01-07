# SQL Query: Tổng hợp số tiền giao dịch

## SQL Template
```sql
SELECT 
    COUNT(*) as total_transactions,
    SUM(amount_transfer) as total_amount,
    AVG(amount_transfer) as avg_amount,
    MIN(amount_transfer) as min_amount,
    MAX(amount_transfer) as max_amount
FROM transaction 
WHERE (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
  AND trans_time BETWEEN '{start_date}' AND '{end_date}'
  AND trans_status = 'S';
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Tổng số tiền đã giao dịch trong tháng này là bao nhiêu?
2. Cho tôi biết tổng tiền chuyển đi trong tuần qua
3. Tính tổng số tiền nhận được trong tháng 12
4. Xem tổng giá trị giao dịch của tài khoản
5. Tra cứu tổng tiền đã chi tiêu trong quý này
6. Cho biết số tiền trung bình mỗi giao dịch
7. Tổng cộng bao nhiêu tiền đã giao dịch hôm nay?
8. Xem tổng số tiền chuyển khoản trong năm 2024
9. Tính toán tổng giá trị các giao dịch thành công
10. Cho tôi biết tổng tiền đã thanh toán hóa đơn
11. Tổng số tiền giao dịch từ đầu tháng đến nay
12. Xem tổng tiền đã nạp vào tài khoản
13. Tra cứu tổng số tiền đã rút ra trong tháng
14. Cho biết giao dịch lớn nhất là bao nhiêu tiền
15. Tìm giao dịch có số tiền nhỏ nhất
16. Tổng số lần giao dịch trong 30 ngày qua là bao nhiêu?
17. Xem tổng chi tiêu qua thẻ trong tháng này
18. Tính tổng tiền đã chuyển cho người khác
19. Cho biết trung bình mỗi ngày giao dịch bao nhiêu tiền
20. Tổng hợp các giao dịch theo tháng trong năm
