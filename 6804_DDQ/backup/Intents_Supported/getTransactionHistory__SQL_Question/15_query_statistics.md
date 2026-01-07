# SQL Query: Thống kê giao dịch theo nhóm

## SQL Template
```sql
SELECT 
    DATE_FORMAT(trans_time, '%Y-%m') as month,
    trans_type,
    COUNT(*) as total_count,
    SUM(amount_transfer) as total_amount,
    AVG(amount_transfer) as avg_amount
FROM transaction 
WHERE (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
  AND trans_time BETWEEN '{start_date}' AND '{end_date}'
  AND trans_status = 'S'
GROUP BY DATE_FORMAT(trans_time, '%Y-%m'), trans_type
ORDER BY month DESC, total_amount DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Thống kê giao dịch theo tháng trong năm 2024
2. Cho tôi báo cáo giao dịch theo từng loại
3. Tìm số lượng giao dịch theo ngày
4. Liệt kê thống kê giao dịch theo quý
5. Tra cứu số lần giao dịch theo từng tuần
6. Cho biết xu hướng giao dịch theo thời gian
7. Xem báo cáo tổng hợp giao dịch tháng 12
8. Tìm tháng có nhiều giao dịch nhất
9. Liệt kê số tiền giao dịch trung bình theo tháng
10. Tra cứu thống kê chi tiêu theo danh mục
11. Cho xem biểu đồ giao dịch theo thời gian
12. Tìm ngày có số tiền giao dịch cao nhất
13. Xem phân tích giao dịch theo loại hình
14. Liệt kê top 5 loại giao dịch phổ biến nhất
15. Tra cứu tỷ lệ giao dịch thành công/thất bại
16. Cho biết số lượng giao dịch mỗi ngày trong tuần
17. Tìm thống kê giao dịch theo khung giờ
18. Xem báo cáo so sánh giao dịch tháng này với tháng trước
19. Liệt kê thống kê giao dịch theo kênh
20. Tra cứu xu hướng chi tiêu trong 6 tháng qua
