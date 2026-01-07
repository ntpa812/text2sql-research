# SQL Query: Tra cứu giao dịch theo trạng thái

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, from_account_no, to_account_no, 
       amount_transfer, amount_currency, trans_status, response_status, trans_desc
FROM transaction 
WHERE trans_status = '{status}'
  AND (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch đã thành công
2. Cho tôi danh sách giao dịch thất bại
3. Tìm những giao dịch đang chờ xử lý
4. Liệt kê các giao dịch bị hủy
5. Tra cứu giao dịch có trạng thái pending
6. Cho biết giao dịch nào đang chờ duyệt
7. Xem các giao dịch đã hoàn thành trong ngày
8. Tìm giao dịch có trạng thái lỗi
9. Liệt kê các giao dịch đã được phê duyệt
10. Tra cứu giao dịch bị từ chối
11. Cho xem những giao dịch chưa hoàn tất
12. Tìm các giao dịch có trạng thái thành công
13. Xem danh sách giao dịch đang xử lý
14. Liệt kê giao dịch có response thành công
15. Tra cứu các giao dịch đã bị hết thời gian
16. Cho biết giao dịch nào đang chờ phản hồi
17. Tìm giao dịch có trạng thái completed
18. Xem các giao dịch failed trong tháng này
19. Liệt kê giao dịch có lỗi hệ thống
20. Tra cứu giao dịch đã được xác nhận
