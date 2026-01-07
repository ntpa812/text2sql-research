# SQL Query: Tra cứu giao dịch theo người nhận

## SQL Template
```sql
SELECT trans_id, trans_time, trans_type, 
       from_account_no, from_account_fullname,
       to_account_no, to_account_fullname, to_user_name,
       amount_transfer, amount_currency,
       trans_status, trans_desc, to_message
FROM transaction 
WHERE from_account_no = '{account_number}'
  AND (to_account_fullname LIKE '%{recipient_name}%' 
       OR to_account_no = '{recipient_account}')
ORDER BY trans_time DESC;
```

## Các câu hỏi mẫu (10-20 câu hỏi với cùng mục tiêu)

1. Xem các giao dịch chuyển cho Nguyễn Văn A
2. Cho tôi danh sách giao dịch đến tài khoản 0123456789
3. Tìm các lần chuyển tiền cho anh Minh
4. Liệt kê giao dịch chuyển đến chị Lan
5. Tra cứu giao dịch với người nhận là Trần Văn B
6. Cho biết tôi đã chuyển cho Nguyễn Thị C bao nhiêu tiền
7. Xem lịch sử giao dịch với số tài khoản 9876543210
8. Tìm các giao dịch đến tài khoản của vợ/chồng
9. Liệt kê chuyển tiền cho bố mẹ
10. Tra cứu giao dịch đến công ty ABC
11. Cho xem các lần chuyển tiền cho Phạm Văn D
12. Tìm giao dịch chuyển đến ngân hàng Vietcombank
13. Xem danh sách giao dịch với người nhận tên Hoa
14. Liệt kê chuyển tiền cho người có STK 1111222233
15. Tra cứu các giao dịch với đối tác kinh doanh
16. Cho biết tôi đã chuyển bao nhiêu lần cho số TK này
17. Tìm tổng tiền đã chuyển cho Nguyễn Văn E
18. Xem các giao dịch gần nhất đến tài khoản 5555666677
19. Liệt kê giao dịch chuyển cho người thân trong tháng
20. Tra cứu lịch sử chuyển tiền cho nhân viên
