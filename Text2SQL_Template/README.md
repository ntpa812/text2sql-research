# Template-based Text-to-SQL + Controlled Generation

## 📂 Cấu trúc dự án

```text
Project_Root/
├── configs/                   
│   ├── dictionary.py           # Từ điển ngữ nghĩa & mapping từ vựng
│   └── __init__.py
│
├── rule_engine/                # [MODULE 1] Generator
│   ├── profiler.py             # Phân tích file Excel -> Semantic Profile
│   ├── generator.py            # Logic sinh câu hỏi & SQL (Spot & Map)
│   ├── faker_utils.py          # Sinh dữ liệu giả (Tên, ngày, số...)
│   ├── grammar_templates.py    # Kho mẫu câu tự nhiên đa dạng
│   └── __init__.py
│
├── sql_parser/                 # [MODULE 2] Parser
│   ├── core.py                 # Logic dịch NLQ -> SQL
│   ├── batch_worker.py         # Xử lý file Excel hàng loạt
│   └── __init__.py
│
├── data/                       # [INPUT] Kho dữ liệu đầu vào
│   ├── source_tables/          # Chứa file mô tả bảng (transaction.xlsx, customer.xlsx...)
│   ├── semantic_profiles/      # Chứa file JSON (Sinh ra từ Profiler)
│   └── parser_inputs/           # Chứa file Excel câu hỏi cần test (test_questions.xlsx)
│
├── outputs/                    # [OUTPUT] Kho dữ liệu đầu ra
│   ├── generated_datasets/     # Dataset huấn luyện đã sinh (ddq_autogen_....xlsx)
│   └── parser_outputs/         # Kết quả test parser kèm SQL
│
├── generate_data.py            # Script chạy Module 1 (Sinh dữ liệu)
├── test_parser.py              # Script chạy Module 2 (Test Parser)
└── requirements.txt            # Các thư viện cần thiết

```

---

## ⚙️ Quy trình hoạt động

Hệ thống bao gồm 2 luồng xử lý độc lập:

### 1. Generator

* **Input:** File Excel mô tả bảng database (Tên cột, Mô tả).
* **Bước 1 - Profiling:** Tự động gán nhãn vai trò cột (`IDENTITY`, `METRIC`, `DIMENSION`, `TEMPORAL`) dựa trên Regex.
* **Bước 2 - Generation:** Sử dụng *Grammar Templates* và *Faker* để sinh ra hàng trăm cặp `(Câu hỏi tự nhiên, SQL query)` cho mỗi bảng.
* **Output:** File Excel chứa dataset dùng để train AI hoặc làm tài liệu tra cứu.

### 2. Parser

* **Input:** Câu hỏi tiếng Việt của người dùng (Ví dụ: "Tổng tiền giao dịch lỗi hôm qua").
* **Logic:** Sử dụng chiến lược **"Spot & Map"**:
* *Intent Detection:* Xác định ý định (Tra cứu/Tính tổng).
* *Entity Extraction:* Trích xuất Ngày tháng, Con số.
* *Column Mapping:* Ánh xạ từ khóa sang tên cột dựa trên `configs/dictionary.py`.

* **Output:** Câu lệnh SQL thực thi được.

---

## 🚀 Hướng dẫn sử dụng

### 1. Cài đặt môi trường

Yêu cầu Python 3.10+ và các thư viện:

```bash
pip install pandas openpyxl faker
```

### 2. Chạy Module Generator

Dùng để tạo dữ liệu training từ file mô tả bảng.

1. Copy file Excel mô tả bảng (ví dụ `transaction.xlsx`) vào thư mục `data/source_tables/`
   
2. Chạy lệnh:
```bash
python generate_data.py
```

3. Kết quả sẽ nằm tại `outputs/generated_datasets/`.

### 3. Chạy Module Parser (Test Dịch NLQ -> SQL)

Dùng để kiểm thử khả năng hiểu câu hỏi của hệ thống.

1. **Chế độ Test nhanh (Interactive):**
```bash
python test_parser.py
# Chọn option 1 -> Nhập câu hỏi trực tiếp trên màn hình
```

2. **Chế độ Batch (File Excel):**
* Chuẩn bị file Excel chứa câu hỏi (header là `question`) tại `data/parser_tests/`.
* Chạy lệnh:
```bash
python test_parser.py
# Chọn option 2 -> Chọn file input -> Chọn ngữ cảnh bảng
```

* Kết quả kèm SQL sinh ra nằm tại `outputs/parser_results/`.

---

## 🔧 Cấu hình hệ thống

Mọi logic về từ điển đồng nghĩa và quy tắc ánh xạ được quản lý tập trung tại:

* 📂 **`configs/dictionary.py`**

---

## Mô tả Logic xử lý

### Logic Semantic Profiler

Thành phần này đóng vai trò "đọc hiểu" cấu trúc dữ liệu thô từ file Excel để gán cho chúng các ý nghĩa nghiệp vụ (Business Semantics).

#### Cơ chế hoạt động

* **Phân loại vai trò** 
  * **IDENTITY:** Các cột định danh duy nhất (Primary Key/Foreign Key) dùng cho các câu hỏi "Tra cứu chi tiết".
  * **DIMENSION:** Các cột chứa thuộc tính phân loại (Trạng thái, Chi nhánh) dùng để tạo điều kiện `WHERE` hoặc `GROUP BY`.
  * **METRIC:** Các cột chứa giá trị số (Số tiền, Phí) dùng cho các hàm tổng hợp như `SUM`, `AVG`.
  * **TEMPORAL:** Các cột ngày tháng dùng để lọc dữ liệu theo thời gian (Sao kê, báo cáo tháng).

* **Gợi ý từ khóa:** Dựa trên tên cột (ví dụ: `trans_status`), Profiler tự động gợi ý các từ khóa tiếng Việt tương ứng như "trạng thái", "tình trạng" để làm đầu vào cho bước sinh câu hỏi.

---

### Logic Rule-Based Generator

Sau khi đã có "bản đồ ngữ nghĩa" từ Profiler, Generator sẽ thực hiện việc "nhân bản" các mẫu câu hỏi bằng thuật toán tổ hợp.

#### Cơ chế hoạt động

* **Sử dụng Bộ từ điển:** Đây là nơi lưu trữ các biến thể ngôn ngữ tự nhiên. Việc tách biệt Vocab giúp bạn dễ dàng mở rộng hệ thống mà không cần sửa code logic.

* **Thuật toán tổ hợp:** Hệ thống sử dụng `itertools.product` để ghép nối các thành phần theo công thức:

> **[Hành động] + [Đối tượng bảng] + [Từ nối] + [Tên cột đồng nghĩa] + {Giá trị mẫu}**

* *Ví dụ:* `["Tra cứu"]` + `["giao dịch"]` + `["có"]` + `["trạng thái"]` + `"{thành công}"`
* Kết quả: "Tra cứu giao dịch có trạng thái thành công".

* **Template Mapping:** Mỗi Role từ bước Semantic sẽ đi kèm với một mẫu SQL tương ứng:
  * `DIMENSION` -> `SELECT * FROM table WHERE col = 'value'`.
  * `METRIC` -> `SELECT SUM(col) FROM table ...`.

---
