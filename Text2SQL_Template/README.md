## Workflow

#### 1. Input:
Nhận tên bảng (ví dụ `transaction`) và file mô tả `transaction.xlsx`

#### 2. Profiler Engine:
* Đọc `transaction.xlsx`
* Phân tích cột `reference_id` $\rightarrow$ Gán nhãn `PK` (Primary Key) 
* Phân tích cột `amount_transfer` $\rightarrow$ Gán nhãn `METRIC`
* Phân tích cột `trans_time` $\rightarrow$ Gán nhãn `TIME`
  
#### 3. Generator Engine:
* Thấy có `METRIC` + `TIME` $\rightarrow$ Tự động sinh SQL thống kê tiền theo thời gian
* Thấy có `PK` $\rightarrow$ Tự động sinh SQL tra cứu chi tiết

#### 4. Output:
Xuất ra file Excel chứa hàng trăm câu hỏi và SQL tương ứng mà không cần AI phải suy nghĩ, đảm bảo chính xác tuyệt đối các slot NER như `{{trans_id}}`, `{{start_date}}`
