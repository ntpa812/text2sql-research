# SQL Query: Tra cứu giao dịch thanh toán hóa đơn

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, 
       from_account_no, amount_transfer, amount_currency,
       bill_type, bill_code, bill_customer_code, bill_customer_name,
       bill_amount, bill_from_date, bill_to_date, bill_cycle,
       partner_code, trans_status, trans_desc
FROM transaction 
WHERE from_account_no = '{account_number}'
  AND bill_type IS NOT NULL
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch thanh toán hóa đơn
2. Cho tôi danh sách các lần đóng tiền điện
3. Tìm giao dịch thanh toán tiền nước
4. Liệt kê các hóa đơn đã thanh toán trong tháng
5. Tra cứu lịch sử đóng tiền internet
6. Cho biết các giao dịch thanh toán tiền điện thoại
7. Xem giao dịch đóng phí bảo hiểm
8. Tìm các lần thanh toán hóa đơn truyền hình cáp
9. Liệt kê giao dịch thanh toán học phí
10. Tra cứu các hóa đơn tiền điện đã đóng
11. Cho xem lịch sử thanh toán hóa đơn viễn thông
12. Tìm giao dịch đóng tiền gas
13. Xem danh sách thanh toán hóa đơn điện nước
14. Liệt kê các lần thanh toán phí dịch vụ
15. Tra cứu giao dịch thanh toán tiền thuê nhà
16. Cho biết tôi đã thanh toán những hóa đơn nào
17. Tìm các giao dịch đóng phí quản lý chung cư
18. Xem lịch sử thanh toán hóa đơn EVN
19. Liệt kê các hóa đơn VNPT đã đóng
20. Tra cứu giao dịch thanh toán Viettel
