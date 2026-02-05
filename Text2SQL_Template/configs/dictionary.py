
COMMON_DICTIONARY = {

    "tables": {
        "transaction": ["giao dịch", "lịch sử chuyển tiền", "sao kê", "lệnh", "gd", "log", "biến động"],
        "customer": ["khách hàng", "người dùng", "kh", "user", "chủ tk"],
        "account": ["tài khoản", "số tài khoản", "tk", "stk", "acc"],
        "credit_card": ["thẻ tín dụng", "thẻ visa", "thẻ mastercard"], # chưa có trong db
        "savings": ["sổ tiết kiệm", "khoản tiết kiệm"] # chưa có trong db
    },

    "suffixes": {
        "_id": ["mã", "số định danh", "id", "số"],
        "_no": ["số", "mã số"],
        "_code": ["mã", "code", "loại"],
        "_date": ["ngày", "thời gian", "hôm"],
        "_time": ["giờ", "thời điểm", "lúc"],
        "_bal": ["số dư", "tiền trong tk", "dư nợ"],
        "_balance": ["số dư", "dư nợ hiện tại"],
        "_channel": ["kênh", "qua"], 
        "_amt": ["số tiền", "giá trị", "khoản tiền"],
        "_amount": ["số tiền", "giá trị", "trị giá"],
        "_val": ["giá trị"],
        "_fee": ["phí", "tiền phí"],
        "_rate": ["lãi suất", "tỷ lệ", "phần trăm"],
        "_status": ["trạng thái", "tình trạng", "kết quả"],
        "_type": ["loại", "hình thức", "kiểu"],
        "_name": ["tên", "họ tên"],
        "_desc": ["nội dung", "mô tả", "ghi chú"],
        "_branch": ["chi nhánh", "phòng giao dịch", "pgd", "nơi mở"],
        "_currency": ["loại tiền", "đơn vị", "nguyên tệ"],
        "_fullname": ["tên đầy đủ", "họ và tên", "chủ tài khoản"],
        "from_": ["từ"],
        "to_": ["đến", "tới"],
        "_do:" : ["thực hiện"],
    },

    "specific_columns": {
        "cif_no": ["mã khách hàng", "số cif", "mã định danh khách hàng"],
        "trans_id": ["mã giao dịch", "số tham chiếu", "mã lệnh"],
        "reference_id": ["mã tham chiếu", "số bút toán", "số ref"],
        "amount_transfer": ["số tiền giao dịch", "số tiền chuyển"],
        "trans_desc": ["nội dung chuyển tiền", "lời nhắn"],
        "effective_date": ["ngày hiệu lực"],
        "expire_date": ["ngày hết hạn", "ngày đáo hạn"],
        "amount": ["số tiền giao dịch", "giá trị giao dịch"],
        "vat_amount": ["tiền thuế", "thuế vat", "giá trị thuế"],
        "discount_amount": ["tiền chiết khấu", "số tiền được giảm", "khuyến mãi"],
        "partner_discount_amount": ["chiết khấu đối tác", "tiền đối tác giảm"],
        "to_amount": ["số tiền thực nhận", "tiền đến", "số tiền đích"],
        "block_amount": ["tiền phong tỏa", "tiền bị giữ", "số dư bị lock"],
        "fee_amount": ["phí dịch vụ", "tiền phí"],
        "original_amount": ["số tiền gốc", "giá trị ban đầu"],
        "parent_id": ["giao dịch gốc", "mã lệnh cha", "giao dịch cha"],  
        "node_id": ["mã node", "id máy chủ", "phân vùng"],     
        "trans_code": ["loại hình", "mã loại giao dịch"],
        "channel_receiver": ["kênh nhận", "nguồn nhận"],
        "reference_number": ["số tham chiếu", "mã bút toán"],
        "account_number": ["số tài khoản", "stk", "số tk"],
        "digital_operation": ["giao dịch số", "giao dịch điện tử"],
        "respone_status": ["trạng thái phản hồi", "kết quả trả về"],
        "approve_status": ["trạng thái phê duyệt", "kết quả duyệt"],
        "bill_payment": ["thanh toán hóa đơn", "trả tiền bill"],
        "bill_type": ["loại hóa đơn", "mã bill"],
        "technical_timestamp": ["dấu thời gian", "thời điểm kỹ thuật"],
        "finish_time": ["thời gian kết thúc", "giờ hoàn thành"]
    },
    
    "values": {
            "STATUS": {
                "FAIL": ["lỗi", "thất bại", "bị treo"],
                "SUCCESS": ["thành công", "hoàn tất", "đã xong"],
                "PENDING": ["đang chờ", "treo", "xử lý"],
                "TIMEOUT": ["quá giờ", "hết hạn"]
            },
            
            "ACCOUNT_TYPE": {
                "PAYMENT": ["tài khoản thanh toán", "tktt", "tài khoản thường"],
                "SAVING": ["tài khoản tiết kiệm", "sổ tiết kiệm"],
                "LOAN": ["tài khoản vay", "khoản vay"],
                "CREDIT": ["thẻ tín dụng", "tài khoản thẻ"]
            },

            "TRANS_TYPE": {
                "CK_NOI_BO": ["chuyển nội bộ", "chuyển cùng ngân hàng"],
                "CK_LIEN_NGAN_HANG": ["chuyển liên ngân hàng", "chuyển ra ngoài"],
                "CK_247": ["chuyển nhanh", "napas 247"],
                "BILL_ELECTRIC": ["tiền điện", "hóa đơn điện"],
                "BILL_WATER": ["tiền nước", "hóa đơn nước"],
                "TOPUP": ["nạp tiền điện thoại", "nạp thẻ"],
                "QR_PAY": ["quét mã qr", "thanh toán qr"]
            },

            "CHANNEL": {
                "APP": ["mobile app", "ứng dụng", "trên app"],
                "WEB": ["internet banking", "trên web", "i-banking"],
                "ATM": ["cây atm", "tại atm", "máy rút tiền"],
                "COUNTER": ["tại quầy", "chi nhánh", "quầy giao dịch"]
            },

            "CURRENCY": {
                "VND": ["đồng", "việt nam đồng", "vnđ"],
                "USD": ["đô", "đô la", "usd"]
            },
            "LOAN_PROD": {"MORTGAGE": ["vay mua nhà", "vay thế chấp"], "CAR": ["vay mua xe"]},
            
            "BRANCH": {"HN": ["chi nhánh hà nội", "cn hoàn kiếm"], "HCM": ["cn sài gòn"]}
        },
    
    "time_phrases": {
            "TODAY": ["hôm nay", "trong ngày", "nay"],
            "YESTERDAY": ["hôm qua", "hôm kia"],
            "THIS_WEEK": ["tuần này", "trong tuần"],
            "LAST_WEEK": ["tuần trước", "tuần rồi"],
            "THIS_MONTH": ["tháng này", "trong tháng"],
            "LAST_MONTH": ["tháng trước", "tháng rồi", "tháng vừa qua"],
            "LAST_QUARTER": ["quý trước", "3 tháng qua", "quý vừa rồi"],
            "YTD": ["đầu năm nay", "từ đầu năm", "năm nay", "từ 1/1"]
        },    
    
    "verbs": {
                "lookup": ["Tra cứu", "Tìm", "Hiển thị", "Cho tôi xem", "Xem chi tiết", "Kiểm tra", "Liệt kê", "Search"],
                "agg": ["Tính tổng", "Tổng cộng", "Thống kê", "Cộng", "Xem tổng"],
                "filter": ["Lọc các", "Danh sách", "Những", "Các"],
            },
    
    "nouns": {
                "table": ["giao dịch", "lệnh chuyển tiền", "biến động số dư", "history"],
                "record": ["bản ghi", "thông tin", "dữ liệu"],
            },
    
    "connectors": ["có", "theo", "với", "của", "tại", "mang"],
    
    "col_mapping": {
        "amount": ["số tiền", "giá trị", "hạn mức", "tiền chuyển"],
        "fee": ["phí", "tiền phí", "phí giao dịch"],
        "status": ["trạng thái", "tình trạng", "kết quả"],
        "type": ["loại", "hình thức", "phân loại"],
        "channel": ["kênh", "nguồn", "phương thức"],
        "time": ["thời gian", "ngày", "giờ", "thời điểm"],
        "user": ["người dùng", "khách hàng", "chủ thẻ"],
        "bank": ["ngân hàng", "tổ chức tín dụng"],
        "id": ["mã", "số", "id", "số hiệu"],
        "trans": ["giao dịch", "lệnh", "bút toán"],
        "product": ["sản phẩm", "dịch vụ", "loại hình"],
        "session": ["phiên", "lần", "version"],
        "action": ["hành động", "động thái", "thao tác"],
        "account": ["tài khoản", "số tài khoản", "stk"],
        "request": ["yêu cầu", "đề nghị", "lệnh"],
        "cust": ["khách hàng", "người dùng", "chủ tk"],
        "from": ["từ"],
        "to": ["đến", "tới"],
        "class": ["loại", "hạng", "phân loại"],
        "currency": ["tiền tệ", "đơn vị", "loại tiền"],
        "system": ["hệ thống", "nền tảng", "ứng dụng"],
        "from_account_fullname": ["người gửi", "người chuyển", "bên đi"],
        "to_account_fullname": ["người nhận", "người hưởng", "bên đến"],
        "fee_affect_object": ["người trả phí", "ai chịu phí"],
        "bill_total_consumption": ["chỉ số điện", "số nước", "sản lượng tiêu thụ"],
        "request": ["yêu cầu"],
        "original": ["gốc", "ban đầu"],
        "customer": ["khách hàng", "người dùng"],
        "class": ["loại", "hạng"],
        "commission": ["hoa hồng", "phí môi giới"],
        "ref": ["tham chiếu", "mã tham chiếu"],
        "reverted": ["hoàn trả", "được hoàn lại"],
        "receiver": ["người nhận", "bên hưởng"],
        "example": ["ví dụ", "mẫu", "dạng"],
        "respone": ["phản hồi", "trả về"],
        "approve": ["phê duyệt", "duyệt"],
        "payment": ["thanh toán", "trả tiền"],
        "bill": ["hóa đơn"],
        "source": ["nguồn", "nguồn gốc"],
        "method": ["phương thức", "cách thức", "hình thức"],
        "cif": ["mã khách hàng", "số cif"],
        "number": ["số"],
        "reference": ["tham chiếu"],
        "digital": ["số", "kỹ thuật số"],
        "operation": ["hoạt động", "thao tác"],
        "do:": ["thực hiện"],
    },
    
    "abbreviations": {
        "stk": "số tài khoản",
        "tk": "tài khoản",
        "ck": "chuyển khoản",
        "gd": "giao dịch",
        "sd": "số dư",
        "gt": "giá trị",
        "nd": "nội dung",
        "nh": "ngân hàng",
        "ls": "lịch sử",
        "cif": "mã khách hàng",
        "dv": "dịch vụ",
        "tn": "tin nhắn"
    },
    
    "category_mapping": {

        "status": "STATUS",
        "trang_thai": "STATUS",
        "tinh_trang": "STATUS",

        "account_type": "ACCOUNT_TYPE",
        "loai_tk": "ACCOUNT_TYPE",
        "acct_type": "ACCOUNT_TYPE",

        "channel": "CHANNEL",
        "kenh": "CHANNEL",
        "source": "CHANNEL",

        "trans_type": "TRANS_TYPE",
        "service": "TRANS_TYPE",
        "loai_gd": "TRANS_TYPE",

        "loan_product": "LOAN_PROD", 
        "term": "TERM",              
        "branch": "BRANCH"           
    },
}