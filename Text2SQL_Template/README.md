# 📊 Text-to-SQL Rule-Based Engine

## 📂 Cấu trúc thư mục

```text
Text2SQL_Template/
├── rule_engine/
│   ├── data/                # Chứa file Excel đầu vào (transaction.xlsx, customer.xlsx...)
│   ├── profiles/            # Chứa kết quả phân tích ngữ nghĩa (.json)
│   ├── output/              # Chứa dataset cuối cùng (.xlsx)
│   ├── profiler.py          # Module phân tích cấu trúc và vai trò của cột
│   ├── generator.py         # Module sinh câu hỏi tự nhiên dựa trên luật (Rule-based)
│   ├── run_profiler.py      # Script chạy riêng phần phân tích
│   ├── run_pipeline.py      # Script chạy toàn bộ quy trình tự động
│   └── __init__.py

```

## ⚙️ Quy trình hoạt động

Hệ thống hoạt động theo mô hình Pipeline 2 bước chính:

### 1. Semantic Profiling

Module `profiler.py` sẽ đọc các file Excel trong thư mục `data/` để xác định vai trò của từng cột dữ liệu:

* **IDENTITY**: Các cột mã định danh (ID, mã giao dịch).
* **METRIC**: Các cột định lượng có thể tính toán (Số tiền, phí).
* **DIMENSION**: Các cột phân loại (Trạng thái, loại giao dịch).
* **TEMPORAL**: Các cột thời gian (Ngày giao dịch).

### 2. Data Generation

Module `generator.py` sử dụng bộ từ điển nghiệp vụ ngân hàng (`dictionary.py`) để tổ hợp và tạo ra các câu hỏi mẫu.

* **Tự động hóa từ đồng nghĩa**: Chuyển đổi "amount" thành "số tiền", "giá trị", "hạn mức"...
* Các ví dụ câu hỏi trong cùng một ô Excel được tách biệt bằng ký tự xuống dòng (`\n`), giúp dễ dàng kiểm soát khi bật tính năng Wrap Text.

## 🚀 Hướng dẫn sử dụng

### Cài đặt môi trường

Yêu cầu Python 3.10+ và các thư viện hỗ trợ:

```bash
pip install pandas openpyxl

```

### Pipeline

Để xử lý file dữ liệu và xuất ra file Excel kết quả cuối cùng, đứng tại thư mục gốc (`Text2SQL_Template`) và chạy:

```bash
python main.py

```

### Chạy riêng lẻ từng module

* **Để cập nhật Profile:** `python -m rule_engine.run_profiler`
* **Để sinh lại Dataset từ Profile có sẵn:** `python -m rule_engine.generator`

---
