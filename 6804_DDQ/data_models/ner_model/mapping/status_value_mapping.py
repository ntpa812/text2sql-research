STATUS_VALUE_MAPPING = {
    "COMPLETED": [
        "đã thực hiện", "thực hiện xong",
        "thành công", "đã thành công",
        "hoàn thành", "đã hoàn thành",
        "hoàn tất", "đã hoàn tất",
        "xong", "đã xong", "hoàn thành xong", "đã hoàn thành xong", "hoàn tất xong", "đã hoàn tất xong",
        "xử lý xong", "đã xử lý xong",
        "successful", "completed", "done", "finished", "complete", "success",
        "succeeded", "succeed"
    ],

    "FAILED": [
        "thất bại", "đã thất bại", "bị thất bại",
        "không thành công", "chưa thành công",
        "không hoàn thành", "không hoàn tất",
        "lỗi", "gặp lỗi", "bị lỗi",
        "giao dịch lỗi", "lỗi giao dịch",
        "failed", "unsuccessful", "not successful",
        "lỗi hệ thống", "bị lỗi hệ thống", "gặp lỗi hệ thống",
        "system error", "system failure"
    ],

    "PENDING": [
        "đang chờ", "chờ", "chờ giao dịch",
        "chờ xử lý", "đang chờ xử lý", "chưa xử lý", "chưa được xử lý",
        "chờ phê duyệt", "đang chờ phê duyệt", "chưa phê duyệt", "chưa được phê duyệt",
        "chờ duyệt", "đang chờ duyệt",
        "chờ được duyệt", "đang chờ được duyệt",
        "chưa duyệt", "chưa được duyệt",
        "đang chờ xác nhận", "chưa xác nhận", "chưa được xác nhận", "chờ xác nhận",
        "đang tiếp nhận", "chờ tiếp nhận", "đang chờ tiếp nhận", "chưa tiếp nhận", "chưa được tiếp nhận",
        "pending", "awaiting", "awaiting approval", 
        "to be processed",
        "mới khởi tạo", "vừa khởi tạo", "mới tạo", "vừa tạo",  "vừa mới tạo", "vừa mới khởi tạo", "vừa mới được tạo", "vừa mới được khởi tạo", "mới được tạo", "mới được khởi tạo",
        "mới vừa tạo", "mới vừa khởi tạo", "vừa mới tạo xong", "vừa mới khởi tạo xong", "mới tạo xong", "mới khởi tạo xong",
        "mới nhận", "vừa nhận", "vừa mới nhận", "mới vừa nhận", "mới được nhận", "vừa mới được nhận", "mới vừa được nhận",
        "chưa bắt đầu", "chưa thực hiện", "chưa chạy", 
        "trong hàng đợi", "đang xếp hàng", "chờ đến lượt",
        "bản nháp", "lưu nháp", "chưa kiểm tra", "chưa gửi",
        "init", "initialized", "created", "new", "queued", 
        "in queue", "unprocessed", "to do", "waiting"
    ],

    "CONFIRMED": [
        "đã xác nhận", "đã được xác nhận", "được xác nhận",
        "đã duyệt", "đã được duyệt", "được duyệt",
        "đã phê duyệt", "đã được phê duyệt", "được phê duyệt",
        "confirmed", "acknowledged", "verified", "validated", "validated successfully",
        "approved", "approval granted",
        "đã chấp thuận", "chấp thuận", "đã được chấp thuận", "đã thông qua", "đã được thông qua",
        "đã kiểm duyệt", "đã được kiểm duyệt", "hợp lệ", "đã xác minh", "đã được xác minh",
        "đã tiếp nhận", "đã được tiếp nhận", "tiếp nhận thành công", "đã ghi nhận", "đã được ghi nhận",
        "accepted", "authorized", "verified successfully"
    ],

    "PROCESSING": [
        "đang xử lý", "đang hoàn thiện", "đang hoàn thành", "đang thực hiện", "đang tiến hành",
        "đang được xử lý", "đang được hoàn thiện", "đang được hoàn thành", "đang được thực hiện", "đang được tiến hành",
        "đang giao dịch", "đang diễn ra",
        "đang thanh toán", "đang xác thực", "đang xác minh", "đang kiểm tra", 
        "đang đối soát", "đang chờ phản hồi", "đang chờ kết quả", "đang truyền dữ liệu",
        "đang chuẩn bị hàng", "đang đóng gói", "đang bàn giao", "đang điều phối",
        "đang giải quyết", "đang được giải quyết", "đang chạy",
        "trong quá trình xử lý", "trong quá trình thực hiện",
        "in progress", "in-progress", "executing", "handling", "running", "processing", "ongoing",
        "under processing", "under execution", "under handling", "under way", "being processed", "being handled",
        "processing request", "processing transaction",
        "treo", "bị treo", "đang treo", "đang bị treo", "hanging"
    ],

    "CANCELLED": [
        "đã hủy", "hủy", "bị hủy", "hủy bỏ", "đã hủy bỏ", "đã được hủy", 
        "hủy giao dịch", "đã đóng", "đóng", "hết hạn", "đã hết hạn", 
        "quá hạn", "hết thời gian", "quá thời gian", "hết thời gian chờ",
        "cancelled", "canceled", "expired", "void", "voided", 
        "aborted", "closed", "rejected_by_user", "rejected by user", "cancelled by user", "canceled by user",
        "từ chối", "đã từ chối", "bị từ chối", "đã bị từ chối", "người dùng từ chối",
        "hủy bỏ bởi người dùng", "ngưng giao dịch", "đã thu hồi", "thu hồi lệnh",
        "rejected", "declined", "revoked", "back by user", "disconnected", "invalidated"
    ],

    "TIMEOUT": [
        "hết thời gian", "quá thời gian", "hết thời gian chờ", "quá thời hạn chờ",
        "timeout", "time out", "timed out", "time-out",
        "hết hạn", "đã hết hạn", "quá hạn", "đã quá hạn", "hết thời hạn",
        "hết phiên làm việc", "hết phiên giao dịch", "giao dịch quá hạn",
        "expired", "has expired", "session expired", "request timeout", 
        "gateway timeout", "connection timeout", "deadline exceeded", "stale",
        "phản hồi chậm", "quá thời gian phản hồi", "vượt quá thời gian", "vượt quá thời gian quy định",
        "hết thời gian thực hiện", "hết thời gian truy cập", "hết phiên",
        "upstream timeout", "read timeout", "connect timeout", "handshake timeout", 
        "socket timeout", "auto-expired", "login timeout", "request-timeout"
    ]

}