# SQL Query: Tra cứu lịch sử giao dịch theo khoảng thời gian

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, from_account_no, to_account_no, 
       amount_transfer, amount_currency, trans_status, trans_desc
FROM transaction 
WHERE trans_time BETWEEN '{start_date}' AND '{end_date}'
  AND (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem lịch sử giao dịch từ ngày 01/12/2024 đến 31/12/2024
2. Cho tôi các giao dịch trong tháng 12 năm 2024
3. Tra cứu giao dịch từ đầu tháng đến nay
4. Liệt kê các giao dịch trong khoảng thời gian từ 01/01/2024 đến 15/01/2024
5. Tôi muốn xem giao dịch trong 7 ngày gần nhất
6. Cho biết các giao dịch phát sinh trong tuần này
7. Kiểm tra giao dịch của tài khoản trong tháng trước
8. Xem các giao dịch từ ngày 15/12/2024 đến hôm nay
9. Tra cứu lịch sử giao dịch quý 4 năm 2024
10. Tìm các giao dịch trong 30 ngày qua
11. Cho xem giao dịch từ ngày 01/11/2024 đến 30/11/2024
12. Hiển thị các giao dịch phát sinh hôm nay
13. Lấy danh sách giao dịch trong khoảng từ đầu năm đến nay
14. Xem sao kê giao dịch tháng 11/2024
15. Tra soát giao dịch từ ngày 10/12 đến 20/12/2024
16. Cho tôi biết các giao dịch trong 3 tháng gần đây
17. Liệt kê giao dịch từ 01/10/2024 đến 31/12/2024
18. Tìm các giao dịch đã thực hiện trong hôm qua
19. Xem các giao dịch trong nửa đầu tháng 12/2024
20. Tra cứu giao dịch từ ngày 01/12 đến ngày 17/12/2024
