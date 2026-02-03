# Template-based Text-to-SQL + Controlled Generation

## 📂 Cấu trúc dự án

```text
Project_Root/
├── configs/                   
│   ├── dictionary.py           # Từ điển thủ công (Kiến thức nền tảng)
│   └── __init__.py
│
├── rule_engine/                # [MODULE 1] Generator & Profiling
│   ├── dict_builder.py         # Logic hợp nhất từ điển 
│   ├── profiler.py             # Phân tích file schema (Regex + AI Suggestion)
│   ├── generator.py            # Logic sinh câu hỏi (nhận Runtime Vocab)
│   ├── faker_utils.py          # Sinh dữ liệu giả
│   ├── grammar_templates.py    # Kho mẫu câu
│   └── __init__.py
│
├── sql_parser/                 # [MODULE 2] Parser
│   ├── core.py                 # Logic dịch NLQ -> SQL
│   ├── batch_worker.py         # Xử lý file Excel hàng loạt
│   └── __init__.py
│
├── data/                       # [INPUT] Kho dữ liệu đầu vào
│   ├── source_tables/          # Chứa file mô tả bảng (transaction.xlsx...)
│   ├── semantic_profiles/      # Chứa file JSON (Sinh ra từ Profiler)
│   └── parser_inputs/          # File test câu hỏi
│
├── outputs/                    # [OUTPUT] Kho dữ liệu đầu ra
│   ├── generated_datasets/     # Dataset huấn luyện đã sinh
│   └── parser_outputs/         # Kết quả test parser
│
├── generate_data.py            # Script chạy Module 1: Profiler -> Builder -> Generator
├── test_parser.py              # Script chạy Module 2
└── requirements.txt            # Các thư viện cần thiết

```

---

## ⚙️ Quy trình hoạt động

Hệ thống bao gồm 2 luồng xử lý:

### 1. Generator (Pipeline)

Quy trình sinh dữ liệu chạy qua 3 bước liên tiếp cho mỗi file schema database đầu vào:

* **Bước 1 - Enhanced Profiling:** * Đọc file mô tả.
* Gán nhãn vai trò cột (`IDENTITY`, `METRIC`...)
* Trích xuất và làm sạch từ khóa từ cột "Mô tả"
* Loại bỏ các từ chuyên ngành DB (Primary Key, Nullable...) để lấy ngữ nghĩa nghiệp vụ

* **Bước 2 - Dictionary Learning:**
* Load từ điển thủ công (`configs/dictionary.py`) làm gốc
* Hợp nhất với các từ khóa vừa học được từ Bước 1
* Tạo ra một runtime dictionary chứa cả kiến thức cũ và mới

* **Bước 3 - Generation:** * Sử dụng runtime dictionary để điền vào grammar templates
* Kết hợp faker sinh dữ liệu giả
* **Output:** File Excel chứa dataset (Câu hỏi, SQL, Metadata)

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
pip install pandas openpyxl faker sentence-transformers torch

```

### 2. Chạy Module Generator

Dùng để tạo dữ liệu training từ file mô tả bảng.

1. Copy file Excel mô tả bảng (ví dụ `transaction.xlsx`) vào thư mục `data/source_tables/`

2. Chạy lệnh:

```bash
python generate_data.py
```

3. Hệ thống sẽ tự động:

* Phân tích file -> Lưu profile cho từng table trong `data/semantic_profiles/`
* Học từ vựng -> Cập nhật Dictionary trong bộ nhớ (`configs/dictionary.py`)
* Sinh câu hỏi -> Lưu kết quả tại `outputs/generated_datasets/`.

### 3. Chạy Module Parser (NLQ -> SQL)

Dùng để kiểm thử khả năng hiểu câu hỏi của hệ thống.

1. **Chế độ Test nhanh (Interactive)**
```bash
python test_parser.py
# Chọn option 1 -> Nhập câu hỏi trực tiếp trên màn hình
```

2. **Chế độ Batch (File Excel)**

* Chuẩn bị file Excel chứa câu hỏi (header là `question`) tại `data/parser_tests/`.
* Chạy lệnh:

```bash
python test_parser.py
# Chọn option 2 -> Chọn file input -> Chọn ngữ cảnh bảng
```

* Kết quả kèm SQL sinh ra nằm tại `outputs/parser_results/`.

---

## Mô tả Logic xử lý

### Logic Semantic Profiler

Thành phần này đóng vai trò "đọc hiểu" cấu trúc dữ liệu thô từ file Excel để gán cho chúng các ý nghĩa nghiệp vụ

#### Cơ chế hoạt động

* **Phân loại vai trò**:
  * **IDENTITY:** Các cột định danh duy nhất (Primary Key/Foreign Key) dùng cho các câu hỏi "Tra cứu chi tiết".
  * **DIMENSION:** Các cột chứa thuộc tính phân loại (Trạng thái, Chi nhánh) dùng để tạo điều kiện `WHERE` hoặc `GROUP BY`.
  * **METRIC:** Các cột chứa giá trị số (Số tiền, Phí) dùng cho các hàm tổng hợp như `SUM`, `AVG`.
  * **TEMPORAL:** Các cột ngày tháng dùng để lọc dữ liệu theo thời gian (Sao kê, báo cáo tháng).

* **Gợi ý từ khóa:** Dựa trên tên cột (ví dụ: `trans_status`), Profiler (+ sentence transformers) tự động gợi ý các từ khóa tiếng Việt tương ứng như "trạng thái", "tình trạng" để làm đầu vào cho bước sinh câu hỏi.

#### Logic Dictionary Builder

Đây là cầu nối giữa dữ liệu thô và bộ sinh câu hỏi:

* **Cơ chế Merge:** Luôn ưu tiên `COMMON_DICTIONARY` (cấu hình tay) để đảm bảo độ chính xác tuyệt đối cho các trường quan trọng. Các từ khóa học được từ Excel sẽ được bổ sung vào danh sách đồng nghĩa
* **Dependency Injection:** Dictionary sau khi được build sẽ được đưa vào `Generator`, giúp Generator "thông minh" lên theo từng file Excel mới mà không cần sửa code

### Logic Rule-Based Generator

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
