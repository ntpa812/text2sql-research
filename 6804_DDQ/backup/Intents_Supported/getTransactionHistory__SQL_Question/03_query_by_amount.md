# SQL Query: Tra cứu giao dịch theo số tiền

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, from_account_no, to_account_no, 
       amount_transfer, amount_currency, trans_status, trans_desc
FROM transaction 
WHERE amount_transfer >= {min_amount} AND amount_transfer <= {max_amount}
  AND (from_account_no = '{account_number}' OR to_account_no = '{account_number}')
ORDER BY amount_transfer DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Tìm các giao dịch có số tiền trên 10 triệu đồng
2. Cho xem những giao dịch từ 5 triệu đến 20 triệu
3. Liệt kê giao dịch có giá trị lớn hơn 50.000.000 VND
4. Xem các giao dịch dưới 1 triệu đồng
5. Tìm giao dịch có số tiền từ 1.000.000 đến 5.000.000
6. Tra cứu các giao dịch có giá trị cao trên 100 triệu
7. Cho biết những giao dịch có số tiền nhỏ hơn 500.000đ
8. Xem danh sách giao dịch trong khoảng 10-50 triệu đồng
9. Tìm các giao dịch có giá trị từ 2 triệu trở lên
10. Liệt kê giao dịch có số tiền không quá 10 triệu
11. Tra cứu giao dịch có số tiền bằng 15.000.000 VND
12. Cho xem những giao dịch giá trị lớn nhất
13. Tìm giao dịch có số tiền tối thiểu 20 triệu đồng
14. Xem các giao dịch có giá trị trong khoảng 5-10 triệu
15. Liệt kê giao dịch với số tiền trên 1 tỷ đồng
16. Tra cứu giao dịch có số tiền từ 100.000 đến 1.000.000
17. Cho biết giao dịch nào có giá trị lớn hơn 500 triệu
18. Tìm các giao dịch có số tiền dưới 2 triệu đồng
19. Xem những giao dịch có giá trị từ 50 triệu trở xuống
20. Liệt kê các giao dịch có số tiền chẵn 10.000.000 VND
