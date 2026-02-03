# File này được sinh tự động bởi dict_builder.py
# Vui lòng review trước khi sử dụng.

COMMON_DICTIONARY = {
    "tables": {
        "transaction": [
            "giao dịch",
            "lịch sử chuyển tiền",
            "sao kê",
            "lệnh",
            "gd",
            "log",
            "biến động"
        ],
        "customer": [
            "khách hàng",
            "người dùng",
            "kh",
            "user",
            "chủ tk"
        ],
        "account": [
            "tài khoản",
            "số tài khoản",
            "tk",
            "stk",
            "acc"
        ],
        "credit_card": [
            "thẻ tín dụng",
            "thẻ visa",
            "thẻ mastercard"
        ],
        "savings": [
            "sổ tiết kiệm",
            "khoản tiết kiệm"
        ]
    },
    "suffixes": {
        "_id": [
            "mã",
            "số định danh",
            "id",
            "số"
        ],
        "_no": [
            "số",
            "mã số"
        ],
        "_code": [
            "mã",
            "code",
            "loại"
        ],
        "_date": [
            "ngày",
            "thời gian",
            "hôm"
        ],
        "_time": [
            "giờ",
            "thời điểm",
            "lúc"
        ],
        "_bal": [
            "số dư",
            "tiền trong tk",
            "dư nợ"
        ],
        "_balance": [
            "số dư",
            "dư nợ hiện tại"
        ],
        "_channel": [
            "kênh",
            "qua"
        ],
        "_amt": [
            "số tiền",
            "giá trị",
            "khoản tiền"
        ],
        "_amount": [
            "số tiền",
            "giá trị",
            "trị giá"
        ],
        "_val": [
            "giá trị"
        ],
        "_fee": [
            "phí",
            "tiền phí"
        ],
        "_rate": [
            "lãi suất",
            "tỷ lệ",
            "phần trăm"
        ],
        "_status": [
            "trạng thái",
            "tình trạng",
            "kết quả"
        ],
        "_type": [
            "loại",
            "hình thức",
            "kiểu"
        ],
        "_name": [
            "tên",
            "họ tên"
        ],
        "_desc": [
            "nội dung",
            "mô tả",
            "ghi chú"
        ],
        "_branch": [
            "chi nhánh",
            "phòng giao dịch",
            "pgd",
            "nơi mở"
        ],
        "_currency": [
            "loại tiền",
            "đơn vị",
            "nguyên tệ"
        ],
        "_fullname": [
            "tên đầy đủ",
            "họ và tên",
            "chủ tài khoản"
        ],
        "from_": [
            "từ"
        ],
        "to_": [
            "đến",
            "tới"
        ]
    },
    "specific_columns": {
        "cif_no": [
            "số mã khách hàng",
            "mã khách hàng",
            "mã định danh khách hàng",
            "số cif",
            "số cif mã định danh duy nhất khách hàng ngân hàng"
        ],
        "trans_id": [
            "mã giao dịch",
            "số tham chiếu",
            "mã lệnh",
            "mã định danh giao dịch theo nghiệp vụ phân biệt các giao dịch với nhau"
        ],
        "reference_id": [
            "khóa chính là mã định danh duy nhất mỗi bản ghi giao dịch trong này",
            "số ref",
            "mã tham chiếu",
            "số bút toán"
        ],
        "amount_transfer": [
            "số tiền chuyển",
            "số tiền transfer",
            "số tiền giao dịch",
            "số tiền giao dịch gốc"
        ],
        "trans_desc": [
            "lời nhắn",
            "giao dịch mô tả",
            "nội dung chuyển tiền",
            "giao dịch"
        ],
        "effective_date": [
            "ngày hiệu lực"
        ],
        "expire_date": [
            "ngày hết hạn",
            "ngày đáo hạn"
        ],
        "amount": [
            "số tiền giao dịch",
            "giá trị giao dịch"
        ],
        "vat_amount": [
            "vat số tiền",
            "tiền thuế",
            "số tiền thuế vat",
            "giá trị thuế",
            "thuế vat"
        ],
        "discount_amount": [
            "số tiền được giảm",
            "discount số tiền",
            "số tiền chiết khấu",
            "tiền chiết khấu",
            "khuyến mãi"
        ],
        "partner_discount_amount": [
            "tiền đối tác giảm",
            "số tiền chiết khấu do đối tác tài trợ",
            "chiết khấu đối tác",
            "partner discount số tiền"
        ],
        "to_amount": [
            "đến số tiền",
            "tiền đến",
            "số tiền đích",
            "số tiền thực tế ghi có vào tài khoản người nhận",
            "số tiền thực nhận"
        ],
        "block_amount": [
            "block số tiền",
            "số dư bị lock",
            "tiền bị giữ",
            "số tiền bị phong tỏa tạm thời trước khi hạch toán thực tế",
            "tiền phong tỏa"
        ],
        "fee_amount": [
            "tổng số tiền phí dịch vụ",
            "phí số tiền",
            "tiền phí",
            "phí dịch vụ"
        ],
        "original_amount": [
            "số tiền gốc",
            "giá trị ban đầu"
        ],
        "parent_id": [
            "mã parent",
            "mã lệnh cha",
            "id giao dịch cha dùng trong trường hợp giao dịch này là giao dịch con hoặc một bước trong chuỗi giao dịch phức tạp",
            "giao dịch gốc",
            "giao dịch cha"
        ],
        "node_id": [
            "id máy chủ",
            "mã định danh node nơi giao dịch xử lý",
            "phân vùng",
            "mã node"
        ],
        "trans_code": [
            "mã loại hình giao dịch",
            "mã giao dịch",
            "loại hình",
            "mã loại giao dịch"
        ],
        "channel_receiver": [
            "kênh tiếp nhận giao dịch",
            "nguồn nhận",
            "kênh người nhận",
            "kênh nhận"
        ],
        "reference_number": [
            "số tham chiếu",
            "mã bút toán"
        ],
        "account_number": [
            "số tài khoản",
            "stk",
            "số tk"
        ],
        "digital_operation": [
            "giao dịch số",
            "giao dịch điện tử"
        ],
        "respone_status": [
            "trạng thái phản hồi",
            "kết quả trả về"
        ],
        "approve_status": [
            "kết quả duyệt",
            "trạng thái phê duyệt"
        ],
        "bill_payment": [
            "thanh toán hóa đơn",
            "trả tiền bill"
        ],
        "bill_type": [
            "loại hóa đơn",
            "mã bill"
        ],
        "technical_timestamp": [
            "dấu thời gian",
            "thời điểm kỹ thuật"
        ],
        "finish_time": [
            "finish thời gian",
            "thời gian giao dịch hoàn toàn kết thúc",
            "giờ hoàn thành",
            "thời gian kết thúc"
        ],
        "id": [
            "mã",
            "khóa chính định danh duy nhất mỗi bản ghi tài khoản",
            "số",
            "id tự tăng là khóa chính bản ghi này"
        ],
        "customer_id": [
            "id định danh khách hàng trong nội bộ",
            "mã khách hàng"
        ],
        "customer_no": [
            "mã số khách hàng",
            "số khách hàng",
            "mã số khách hàng với tài khoản"
        ],
        "customer_name": [
            "họ và tên đầy đủ khách hàng",
            "tên khách hàng"
        ],
        "system_id": [
            "id nguồn",
            "mã nguồn cung cấp tài khoản này",
            "mã hệ thống"
        ],
        "cif_branch": [
            "chi nhánh nơi mở/quản lý mã cif này",
            "mã khách hàng chi nhánh"
        ],
        "cif_type": [
            "loại mã khách hàng",
            "loại cif"
        ],
        "address_line": [
            "dòng địa chỉ",
            "address line"
        ],
        "full_address": [
            "địa chỉ đầy đủ",
            "full address"
        ],
        "branch_code": [
            "mã chi nhánh quản lý trực tiếp khách hàng",
            "mã chi nhánh"
        ],
        "customer_class": [
            "loại khách hàng",
            "phân hạng khách hàng"
        ],
        "customer_status": [
            "trạng thái khách hàng",
            "trạng thái hiện khách hàng"
        ],
        "date_of_issue": [
            "ngày cấp giấy tờ định danh",
            "ngày of issue"
        ],
        "email": [
            "địa chỉ thư điện tử khách hàng",
            "email"
        ],
        "home_phone": [
            "số điện thoại bàn/điện thoại cố định",
            "home phone"
        ],
        "identify_id": [
            "số giấy tờ định danh",
            "mã identify"
        ],
        "identify_level": [
            "identify level",
            "cấp độ định danh"
        ],
        "identify_name": [
            "tên identify",
            "loại giấy tờ định danh"
        ],
        "init_date": [
            "ngày khởi tạo khách hàng trên",
            "ngày init"
        ],
        "is_fee_default": [
            "đánh dấu khách hàng có thuộc diện mặc định thu phí hay không",
            "is phí default"
        ],
        "latitude": [
            "vĩ độ",
            "latitude"
        ],
        "longitude": [
            "longitude",
            "kinh độ"
        ],
        "mobile_phone": [
            "mobile phone",
            "số điện thoại di động chính"
        ],
        "nationality_id": [
            "mã nationality",
            "mã quốc tịch"
        ],
        "place_id": [
            "mã place",
            "mã vùng/địa điểm cư trú"
        ],
        "place_of_issue": [
            "place of issue",
            "nơi cấp giấy tờ định danh"
        ],
        "unique_id": [
            "mã định danh duy nhất",
            "mã unique"
        ],
        "unique_value": [
            "giá trị đặc trưng định danh duy nhất khách hàng",
            "unique value"
        ],
        "status": [
            "trạng thái",
            "trạng thái bản ghi",
            "trạng thái tài khoản"
        ],
        "sign_1": [
            "đường dẫn hoặc chữ ký mẫu số khách hàng",
            "sign 1"
        ],
        "sign_2": [
            "sign 2",
            "đường dẫn hoặc chữ ký mẫu số"
        ],
        "sex": [
            "sex",
            "giới tính"
        ],
        "date_of_birth": [
            "ngày tháng năm sinh",
            "ngày of birth"
        ],
        "old_customer_status": [
            "trạng thái cũ khách hàng",
            "trạng thái old khách hàng"
        ],
        "new_customer_status": [
            "trạng thái new khách hàng",
            "trạng thái mới khách hàng"
        ],
        "unique_image_front": [
            "unique image front",
            "đường dẫn ảnh mặt trước giấy tờ định danh"
        ],
        "unique_image_back": [
            "unique image back",
            "đường dẫn ảnh mặt sau giấy tờ định danh"
        ],
        "core_customer_id": [
            "id khách hàng bên lõi map tài khoản với khách hàng",
            "mã core khách hàng"
        ],
        "account_no": [
            "số tài khoản",
            "số tài khoản hoặc số thẻ đây là định danh tài khoản để giao dịch"
        ],
        "account_class": [
            "phân loại tài khoản",
            "loại tài khoản"
        ],
        "primary_account": [
            "primary tài khoản",
            "đánh dấu tài khoản chính thường dùng khi một khách hàng có nhiều tài khoản"
        ],
        "order_no": [
            "số thứ tự hiển thị tài khoản trên giao diện",
            "số order"
        ],
        "verify_status": [
            "trạng thái xác thực tài khoản",
            "trạng thái verify"
        ],
        "check_status": [
            "trạng thái kiểm tra",
            "trạng thái check"
        ],
        "channel_id": [
            "mã kênh",
            "id kênh tạo tài khoản"
        ],
        "priority": [
            "priority",
            "độ ưu tiên tài khoản khi thực hiện các giao dịch tự động"
        ],
        "create_date": [
            "ngày create",
            "ngày mở tài khoản hoặc ngày bản ghi tạo"
        ],
        "account_name": [
            "tên tài khoản"
        ],
        "account_branch": [
            "tài khoản chi nhánh",
            "mã chi nhánh nơi quản lý tài khoản này"
        ],
        "card_mask": [
            "card mask",
            "số thẻ che bớt để đảm bảo bảo mật"
        ],
        "end_date": [
            "ngày end",
            "ngày hết hạn tài khoản hoặc ngày đóng tài khoản"
        ],
        "user_id": [
            "mã người dùng",
            "mã định danh người dùng thực hiện giao dịch"
        ],
        "user_name": [
            "tên người dùng",
            "tên đăng nhập người dùng thực hiện giao dịch"
        ],
        "session_id": [
            "mã phiên làm việc người dùng khi thực hiện giao dịch",
            "mã phiên"
        ],
        "trans_time": [
            "giao dịch thời gian",
            "thời điểm chính xác giao dịch phát sinh"
        ],
        "trans_type": [
            "loại giao dịch",
            "loại giao dịch hoặc nhóm giao dịch"
        ],
        "action_id": [
            "mã hành động cụ thể mà người dùng thực hiện",
            "mã hành động"
        ],
        "stak_user_type_do": [
            "loại người dùng tác nghiệp",
            "stak người dùng loại do"
        ],
        "user_do": [
            "tên hoặc mã nhân viên vận hành/hỗ trợ liên quan đến giao dịch này",
            "người dùng do"
        ],
        "branch_code_do": [
            "chi nhánh mã do",
            "mã chi nhánh nhân viên vận hành/hỗ trợ"
        ],
        "product_id": [
            "mã sản phẩm hoặc dịch vụ liên quan đến giao dịch",
            "mã sản phẩm"
        ],
        "business_process": [
            "business process",
            "tên quy trình nghiệp vụ mà giao dịch này thuộc"
        ],
        "request_id": [
            "mã yêu cầu",
            "mã yêu cầu duy nhất sinh ra từ phía client gửi lên server"
        ],
        "original_request_id": [
            "mã gốc yêu cầu",
            "mã yêu cầu gốc"
        ],
        "input_type": [
            "loại đầu vào",
            "loại input"
        ],
        "input_value": [
            "input value",
            "giá trị đầu vào"
        ],
        "from_system_id": [
            "mã nguồn khởi tạo giao dịch",
            "mã từ hệ thống"
        ],
        "from_cust_id": [
            "id khách hàng người chuyển tiền/người thanh toán",
            "mã từ khách hàng"
        ],
        "from_cust_no": [
            "mã cif hoặc mã khách hàng người chuyển",
            "số từ khách hàng"
        ],
        "from_cust_branch": [
            "từ khách hàng chi nhánh",
            "mã chi nhánh quản lý khách hàng người chuyển"
        ],
        "from_account_class": [
            "loại từ tài khoản",
            "hạng hoặc nhóm tài khoản nguồn"
        ],
        "from_account_type": [
            "loại từ tài khoản",
            "loại tài khoản nguồn"
        ],
        "from_account_no": [
            "số từ tài khoản",
            "số tài khoản người chuyển tiền"
        ],
        "from_account_branch": [
            "từ tài khoản chi nhánh",
            "mã chi nhánh quản lý tài khoản nguồn"
        ],
        "from_account_currency": [
            "từ tài khoản loại tiền",
            "loại tiền tệ tài khoản nguồn"
        ],
        "from_account_fullname": [
            "tên đầy đủ chủ tài khoản nguồn",
            "từ tài khoản tên đầy đủ"
        ],
        "from_message": [
            "từ message",
            "nội dung hoặc lời nhắn từ người chuyển tiền"
        ],
        "to_system_id": [
            "mã đến hệ thống",
            "mã đích ví dụ napas citad core banking"
        ],
        "to_cust_no": [
            "mã khách hàng người thụ hưởng",
            "số đến khách hàng"
        ],
        "to_cust_branch": [
            "đến khách hàng chi nhánh",
            "mã chi nhánh quản lý khách hàng thụ hưởng"
        ],
        "to_account_no": [
            "số tài khoản người nhận tiền",
            "số đến tài khoản"
        ],
        "to_account_branch": [
            "đến tài khoản chi nhánh",
            "mã chi nhánh quản lý tài khoản đích"
        ],
        "to_account_currency": [
            "đến tài khoản loại tiền",
            "loại tiền tệ tài khoản đích"
        ],
        "to_account_fullname": [
            "đến tài khoản tên đầy đủ",
            "tên đầy đủ chủ tài khoản đích"
        ],
        "to_message": [
            "nội dung tin nhắn hiển thị người nhận",
            "đến message"
        ],
        "to_user_name": [
            "tên đăng nhập người nhận",
            "tên đến người dùng"
        ],
        "amount_currency": [
            "số tiền loại tiền",
            "loại tiền tệ số tiền giao dịch"
        ],
        "amount_rate": [
            "tỷ giá quy đổi áp dụng giao dịch",
            "số tiền lãi suất"
        ],
        "block_amount_ref_no": [
            "mã tham chiếu lệnh phong tỏa tiền",
            "số block số tiền tham chiếu"
        ],
        "fee_affect_object": [
            "phí affect object",
            "đối tượng chịu phí"
        ],
        "fee_currency": [
            "phí loại tiền",
            "loại tiền tệ phí"
        ],
        "fee_amount_rate": [
            "phí số tiền lãi suất",
            "tỷ giá quy đổi phí"
        ],
        "fee_ind": [
            "chỉ số hoặc mã loại phí",
            "phí ind"
        ],
        "commission_amount": [
            "số tiền hoa hồng trả đại lý/đối tác",
            "hoa hồng số tiền"
        ],
        "commission_currency": [
            "loại tiền tệ hoa hồng",
            "hoa hồng loại tiền"
        ],
        "commission_rate": [
            "hoa hồng lãi suất",
            "tỷ lệ hoa hồng hưởng"
        ],
        "commission_ind": [
            "hoa hồng ind",
            "chỉ số hoặc mã loại hoa hồng"
        ],
        "promotion_amount": [
            "số tiền khuyến mãi/giảm giá trực tiếp",
            "promotion số tiền"
        ],
        "promotion_currency": [
            "promotion loại tiền",
            "loại tiền tệ khuyến mãi"
        ],
        "promotion_rate": [
            "promotion lãi suất",
            "tỷ lệ khuyến mãi"
        ],
        "promotion_ind": [
            "chỉ số hoặc mã chương trình khuyến mãi",
            "promotion ind"
        ],
        "trans_ref_no": [
            "số tham chiếu giao dịch thường in lên biên lai hoặc tra cứu",
            "số giao dịch tham chiếu"
        ],
        "trans_name": [
            "tên giao dịch",
            "tên hiển thị giao dịch"
        ],
        "trans_info": [
            "giao dịch info",
            "bổ sung dạng text/json"
        ],
        "trans_progress": [
            "giao dịch progress",
            "log tiến trình thực hiện giao dịch"
        ],
        "request_time": [
            "thời gian nhận yêu cầu từ client",
            "yêu cầu thời gian"
        ],
        "request_channel": [
            "yêu cầu kênh",
            "kênh gửi yêu cầu"
        ],
        "trans_request": [
            "giao dịch yêu cầu",
            "lưu toàn bộ nội dung gói tin yêu cầu để phục vụ tra soát/audit"
        ],
        "trans_revert_ref_no": [
            "số giao dịch revert tham chiếu",
            "số tham chiếu giao dịch hoàn tiền/đảo ngược"
        ],
        "partner_code": [
            "mã đối tác tích hợp nếu là thanh toán dịch vụ",
            "mã partner"
        ],
        "response_time": [
            "thời gian phản hồi kết quả client",
            "response thời gian"
        ],
        "response_code": [
            "mã phản hồi từ",
            "mã response"
        ],
        "response_message": [
            "response message",
            "thông báo phản hồi"
        ],
        "response_status": [
            "trạng thái phản hồi ngắn gọn",
            "trạng thái response"
        ],
        "error_code": [
            "mã lỗi kỹ thuật",
            "mã error"
        ],
        "trans_response": [
            "giao dịch response",
            "lưu toàn bộ nội dung gói tin phản hồi để phục vụ tra soát/audit"
        ],
        "checker_id": [
            "id người duyệt giao dịch dùng trong mô hình maker/checker",
            "mã checker"
        ],
        "checker_date": [
            "ngày checker",
            "thời gian duyệt giao dịch"
        ],
        "maker_id": [
            "mã maker",
            "id người tạo lệnh giao dịch dùng trong mô hình maker/checker"
        ],
        "maker_date": [
            "ngày maker",
            "thời gian tạo lệnh"
        ],
        "trans_status": [
            "trạng thái giao dịch",
            "trạng thái cuối cùng giao dịch"
        ],
        "core_system": [
            "tên core banking xử lý hạch toán",
            "core hệ thống"
        ],
        "core_ref_no": [
            "số bút toán sinh ra trong core banking",
            "số core tham chiếu"
        ],
        "core_revert_ref_no": [
            "số core revert tham chiếu",
            "số bút toán đảo trong core banking"
        ],
        "payment_system": [
            "tên cổng thanh toán trung gian",
            "thanh toán hệ thống"
        ],
        "payment_ref_no": [
            "số thanh toán tham chiếu",
            "mã giao dịch tham chiếu cổng thanh toán"
        ],
        "payment_status": [
            "trạng thái trả từ cổng thanh toán",
            "trạng thái thanh toán"
        ],
        "bill_customer_code": [
            "mã khách hàng trên hóa đơn",
            "mã hóa đơn khách hàng"
        ],
        "bill_customer_name": [
            "tên hóa đơn khách hàng",
            "tên khách hàng đứng tên trên hóa đơn dịch vụ"
        ],
        "bill_customer_address": [
            "hóa đơn khách hàng address",
            "địa chỉ khách hàng trên hóa đơn"
        ],
        "bill_customer_phone": [
            "hóa đơn khách hàng phone",
            "số điện thoại liên hệ khách hàng trên hóa đơn"
        ],
        "bill_id": [
            "mã hóa đơn",
            "mã định danh hóa đơn trong"
        ],
        "bill_code": [
            "mã tra cứu hóa đơn",
            "mã hóa đơn"
        ],
        "bill_currency": [
            "loại tiền tệ hóa đơn",
            "hóa đơn loại tiền"
        ],
        "bill_from_date": [
            "ngày bắt đầu kỳ cước hóa đơn",
            "ngày hóa đơn từ"
        ],
        "bill_to_date": [
            "ngày kết thúc kỳ cước hóa đơn",
            "ngày hóa đơn đến"
        ],
        "bill_cycle": [
            "hóa đơn cycle",
            "kỳ thanh toán"
        ],
        "bill_total_consumption": [
            "hóa đơn total consumption",
            "tổng sản lượng tiêu thụ ghi trên hóa đơn"
        ],
        "bill_desc": [
            "hóa đơn",
            "hóa đơn mô tả"
        ],
        "bill_other_info": [
            "hóa đơn other info",
            "khác hóa đơn"
        ],
        "number_of_bills": [
            "số of bills",
            "số lượng hóa đơn thanh toán trong giao dịch này"
        ],
        "insert_time": [
            "insert thời gian",
            "thời gian bản ghi chèn vào cơ sở"
        ],
        "input_amount": [
            "input số tiền",
            "số tiền người dùng nhập vào ban đầu"
        ],
        "receive_time": [
            "receive thời gian",
            "thời gian tiền"
        ],
        "accounting_online": [
            "accounting online",
            "cờ đánh dấu xem giao dịch đã hạch toán online vào core banking chưa"
        ],
        "server_session_id": [
            "mã phiên làm việc phía server",
            "mã server phiên"
        ],
        "source_type": [
            "loại nguồn",
            "loại nguồn tiền"
        ],
        "card_number": [
            "số thẻ nếu nguồn tiền là thẻ",
            "số card"
        ],
        "cust_no_do": [
            "khách hàng số do",
            "mã khách hàng tác nghiệp số"
        ],
        "bill_amount": [
            "hóa đơn số tiền",
            "giá trị tiền ghi trên hóa đơn cần thanh toán"
        ],
        "category_code": [
            "mã danh mục giao dịch",
            "mã category"
        ],
        "app_version": [
            "phiên bản ứng dụng mobile mà khách hàng đang sử dụng để giao dịch",
            "app version"
        ],
        "from_cif_no": [
            "mã cif người chuyển",
            "số từ mã khách hàng"
        ]
    },
    "values": {
        "STATUS": {
            "FAIL": [
                "lỗi",
                "thất bại",
                "bị treo"
            ],
            "SUCCESS": [
                "thành công",
                "hoàn tất",
                "đã xong"
            ],
            "PENDING": [
                "đang chờ",
                "treo",
                "xử lý"
            ],
            "TIMEOUT": [
                "quá giờ",
                "hết hạn"
            ]
        },
        "TRANS_TYPE": {
            "CK_NOI_BO": [
                "chuyển nội bộ",
                "chuyển cùng ngân hàng"
            ],
            "CK_LIEN_NGAN_HANG": [
                "chuyển liên ngân hàng",
                "chuyển ra ngoài"
            ],
            "CK_247": [
                "chuyển nhanh",
                "napas 247"
            ],
            "BILL_ELECTRIC": [
                "tiền điện",
                "hóa đơn điện"
            ],
            "BILL_WATER": [
                "tiền nước",
                "hóa đơn nước"
            ],
            "TOPUP": [
                "nạp tiền điện thoại",
                "nạp thẻ"
            ],
            "QR_PAY": [
                "quét mã qr",
                "thanh toán qr"
            ]
        },
        "CHANNEL": {
            "APP": [
                "mobile app",
                "ứng dụng",
                "trên app"
            ],
            "WEB": [
                "internet banking",
                "trên web",
                "i-banking"
            ],
            "ATM": [
                "cây atm",
                "tại atm",
                "máy rút tiền"
            ],
            "COUNTER": [
                "tại quầy",
                "chi nhánh",
                "quầy giao dịch"
            ]
        },
        "CURRENCY": {
            "VND": [
                "đồng",
                "việt nam đồng",
                "vnđ"
            ],
            "USD": [
                "đô",
                "đô la",
                "usd"
            ]
        }
    },
    "time_phrases": {
        "TODAY": [
            "hôm nay",
            "trong ngày",
            "nay"
        ],
        "YESTERDAY": [
            "hôm qua",
            "hôm kia"
        ],
        "THIS_WEEK": [
            "tuần này",
            "trong tuần"
        ],
        "LAST_WEEK": [
            "tuần trước",
            "tuần rồi"
        ],
        "THIS_MONTH": [
            "tháng này",
            "trong tháng"
        ],
        "LAST_MONTH": [
            "tháng trước",
            "tháng rồi",
            "tháng vừa qua"
        ],
        "LAST_QUARTER": [
            "quý trước",
            "3 tháng qua",
            "quý vừa rồi"
        ],
        "YTD": [
            "đầu năm nay",
            "từ đầu năm",
            "năm nay",
            "từ 1/1"
        ]
    },
    "verbs": {
        "lookup": [
            "Tra cứu",
            "Tìm",
            "Hiển thị",
            "Cho tôi xem",
            "Xem chi tiết",
            "Kiểm tra",
            "Liệt kê",
            "Search"
        ],
        "agg": [
            "Tính tổng",
            "Tổng cộng",
            "Thống kê",
            "Cộng",
            "Xem tổng"
        ],
        "filter": [
            "Lọc các",
            "Danh sách",
            "Những",
            "Các"
        ]
    },
    "nouns": {
        "table": [
            "giao dịch",
            "lệnh chuyển tiền",
            "biến động số dư",
            "history"
        ],
        "record": [
            "bản ghi",
            "thông tin",
            "dữ liệu"
        ]
    },
    "connectors": [
        "có",
        "theo",
        "với",
        "của",
        "tại",
        "mang"
    ],
    "col_mapping": {
        "amount": [
            "số tiền",
            "giá trị",
            "hạn mức",
            "tiền chuyển"
        ],
        "fee": [
            "phí",
            "tiền phí",
            "phí giao dịch"
        ],
        "status": [
            "trạng thái",
            "tình trạng",
            "kết quả"
        ],
        "type": [
            "loại",
            "hình thức",
            "phân loại"
        ],
        "channel": [
            "kênh",
            "nguồn",
            "phương thức"
        ],
        "time": [
            "thời gian",
            "ngày",
            "giờ",
            "thời điểm"
        ],
        "user": [
            "người dùng",
            "khách hàng",
            "chủ thẻ"
        ],
        "bank": [
            "ngân hàng",
            "tổ chức tín dụng"
        ],
        "id": [
            "mã",
            "số",
            "id",
            "số hiệu"
        ],
        "trans": [
            "giao dịch",
            "lệnh",
            "bút toán"
        ],
        "product": [
            "sản phẩm",
            "dịch vụ",
            "loại hình"
        ],
        "session": [
            "phiên",
            "lần",
            "version"
        ],
        "action": [
            "hành động",
            "động thái",
            "thao tác"
        ],
        "account": [
            "tài khoản",
            "số tài khoản",
            "stk"
        ],
        "request": [
            "yêu cầu"
        ],
        "cust": [
            "khách hàng",
            "người dùng",
            "chủ tk"
        ],
        "from": [
            "từ"
        ],
        "to": [
            "đến",
            "tới"
        ],
        "class": [
            "loại",
            "hạng"
        ],
        "currency": [
            "tiền tệ",
            "đơn vị",
            "loại tiền"
        ],
        "system": [
            "hệ thống",
            "nền tảng",
            "ứng dụng"
        ],
        "from_account_fullname": [
            "người gửi",
            "người chuyển",
            "bên đi"
        ],
        "to_account_fullname": [
            "người nhận",
            "người hưởng",
            "bên đến"
        ],
        "fee_affect_object": [
            "người trả phí",
            "ai chịu phí"
        ],
        "bill_total_consumption": [
            "chỉ số điện",
            "số nước",
            "sản lượng tiêu thụ"
        ],
        "original": [
            "gốc",
            "ban đầu"
        ],
        "customer": [
            "khách hàng",
            "người dùng"
        ],
        "commission": [
            "hoa hồng",
            "phí môi giới"
        ],
        "ref": [
            "tham chiếu",
            "mã tham chiếu"
        ],
        "reverted": [
            "hoàn trả",
            "được hoàn lại"
        ],
        "receiver": [
            "người nhận",
            "bên hưởng"
        ],
        "example": [
            "ví dụ",
            "mẫu",
            "dạng"
        ],
        "respone": [
            "phản hồi",
            "trả về"
        ],
        "approve": [
            "phê duyệt",
            "duyệt"
        ],
        "payment": [
            "thanh toán",
            "trả tiền"
        ],
        "bill": [
            "hóa đơn"
        ],
        "source": [
            "nguồn",
            "nguồn gốc"
        ],
        "method": [
            "phương thức",
            "cách thức",
            "hình thức"
        ],
        "cif": [
            "mã khách hàng",
            "số cif"
        ],
        "number": [
            "số"
        ],
        "reference": [
            "tham chiếu"
        ],
        "digital": [
            "số",
            "kỹ thuật số"
        ],
        "operation": [
            "hoạt động",
            "thao tác"
        ]
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
    }
}