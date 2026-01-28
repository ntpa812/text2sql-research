
COMMON_DICTIONARY = {

    "tables": {
        "transaction": ["giao dịch", "lịch sử chuyển tiền", "sao kê", "biến động số dư"],
        "customer": ["khách hàng", "người dùng", "chủ tài khoản"],
        "customer_account": ["tài khoản", "số tài khoản"],
        "credit_card": ["thẻ tín dụng", "thẻ visa", "thẻ mastercard"], #gia dinh
        "savings": ["sổ tiết kiệm", "khoản tiết kiệm"] #gia dinh
    },

    "suffixes": {
        "_id": ["mã", "số định danh", "id", "số"],
        "_no": ["số", "mã số"],
        "_code": ["mã", "code"],
        "_date": ["ngày", "thời gian", "hôm"],
        "_time": ["giờ", "thời điểm", "lúc"],
        "_bal": ["số dư", "tiền trong tk", "dư nợ"],
        "_balance": ["số dư", "dư nợ hiện tại"],
        "_amt": ["số tiền", "giá trị", "khoản tiền"],
        "_amount": ["số tiền", "giá trị", "trị giá"],
        "_val": ["giá trị"],
        "_fee": ["phí", "tiền phí"],
        "_rate": ["lãi suất", "tỷ lệ", "phần trăm"],
        "_status": ["trạng thái", "tình trạng", "kết quả"],
        "_type": ["loại", "hình thức", "kiểu"],
        "_name": ["tên", "họ tên"],
        "_desc": ["nội dung", "mô tả", "ghi chú"]
    },

    "specific_columns": {
        "cif_no": ["mã khách hàng", "số cif", "mã định danh khách hàng"],
        "trans_id": ["mã giao dịch", "số tham chiếu", "mã lệnh"],
        "reference_id": ["mã tham chiếu", "số bút toán"],
        "amount_transfer": ["số tiền giao dịch", "số tiền chuyển"],
        "trans_desc": ["nội dung chuyển tiền", "lời nhắn"],
        "effective_date": ["ngày hiệu lực"],
        "expire_date": ["ngày hết hạn", "ngày đáo hạn"]
    }
}