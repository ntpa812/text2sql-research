# Transaction History SQL Queries & Questions

## Giới thiệu
Thư mục này chứa các câu SQL thường gặp trong ngân hàng để tra cứu lịch sử giao dịch từ bảng `transaction`. Mỗi file SQL đi kèm với 10-20 câu hỏi mẫu với cùng mục tiêu tra cứu nhưng được diễn đạt theo nhiều cách khác nhau.

## Danh sách các SQL Queries

| STT | File | Mô tả | Số câu hỏi |
|-----|------|-------|-----------|
| 01 | [01_query_by_account.md](01_query_by_account.md) | Tra cứu lịch sử giao dịch theo số tài khoản | 20 |
| 02 | [02_query_by_time_range.md](02_query_by_time_range.md) | Tra cứu giao dịch theo khoảng thời gian | 20 |
| 03 | [03_query_by_amount.md](03_query_by_amount.md) | Tra cứu giao dịch theo số tiền | 20 |
| 04 | [04_query_by_status.md](04_query_by_status.md) | Tra cứu giao dịch theo trạng thái | 20 |
| 05 | [05_query_by_trans_type.md](05_query_by_trans_type.md) | Tra cứu giao dịch theo loại giao dịch | 20 |
| 06 | [06_query_sum_amount.md](06_query_sum_amount.md) | Tổng hợp số tiền giao dịch | 20 |
| 07 | [07_query_transfer.md](07_query_transfer.md) | Tra cứu giao dịch chuyển tiền | 20 |
| 08 | [08_query_bill_payment.md](08_query_bill_payment.md) | Tra cứu giao dịch thanh toán hóa đơn | 20 |
| 09 | [09_query_by_channel.md](09_query_by_channel.md) | Tra cứu giao dịch theo kênh | 20 |
| 10 | [10_query_trans_detail.md](10_query_trans_detail.md) | Tra cứu chi tiết một giao dịch cụ thể | 20 |
| 11 | [11_query_receive_money.md](11_query_receive_money.md) | Tra cứu giao dịch nhận tiền | 20 |
| 12 | [12_query_fee.md](12_query_fee.md) | Tra cứu phí giao dịch | 20 |
| 13 | [13_query_by_recipient.md](13_query_by_recipient.md) | Tra cứu giao dịch theo người nhận | 20 |
| 14 | [14_query_card_transaction.md](14_query_card_transaction.md) | Tra cứu giao dịch thẻ | 20 |
| 15 | [15_query_statistics.md](15_query_statistics.md) | Thống kê giao dịch theo nhóm | 20 |

## Tổng quan

- **Tổng số SQL Queries:** 15
- **Tổng số câu hỏi mẫu:** 300 câu
- **Bảng dữ liệu:** `transaction` (ai_bank_gateway schema)

## Cấu trúc bảng Transaction

Bảng `transaction` bao gồm các trường chính:
- `trans_id`: ID giao dịch (Primary Key)
- `trans_time`: Thời gian giao dịch
- `trans_type`: Loại giao dịch
- `trans_status`: Trạng thái giao dịch
- `from_account_no`: Số tài khoản nguồn
- `to_account_no`: Số tài khoản đích
- `amount_transfer`: Số tiền chuyển
- `fee_amount`: Phí giao dịch
- `request_channel`: Kênh giao dịch
- `trans_desc`: Mô tả giao dịch
- `bill_type`, `bill_code`: Thông tin hóa đơn
- `card_number`: Số thẻ

## Cách sử dụng

1. Chọn file SQL phù hợp với yêu cầu tra cứu
2. Thay thế các tham số trong template (ví dụ: `{account_number}`, `{start_date}`, `{end_date}`)
3. Sử dụng các câu hỏi mẫu để training model NLU/Intent Recognition

## Ghi chú

- Các câu hỏi được viết bằng tiếng Việt, phù hợp cho training chatbot ngân hàng
- Mỗi câu hỏi có thể kết hợp với các biến động như số tài khoản, ngày tháng, số tiền cụ thể
- SQL templates sử dụng cú pháp MySQL/MariaDB

---
*Tạo ngày: 17/12/2024*
*Phiên bản: 1.0*
