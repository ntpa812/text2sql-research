import random
from typing import List, Dict

class GrammarLibrary:
    def __init__(self):
        """
        Kho chứa các mẫu câu cho các examples
        
        Quy ước Placeholders:
        - {verb}: Động từ (Tra cứu, tìm, xem...)
        - {noun}: Tên bảng/đối tượng (Giao dịch, tài khoản...)
        - {col_name}: Tên cột (Mã, số dư, trạng thái...)
        - {val}: Giá trị giả lập hoặc slot (12345, 'Thành công'...)
        - {col_metric}: Cột định lượng (Số tiền, phí...)
        - {col_group}: Cột phân nhóm (Trạng thái, Chi nhánh...)
        - {start}, {end}: Thời gian
        """
        self.templates = {

            "IDENTITY": [

                "Vui lòng {verb} thông tin chi tiết của {noun} có {col_name} là {val}",
                "Hãy hiển thị dữ liệu bản ghi {noun} với {col_name} {val}",

                "{verb} {noun} theo {col_name} {val}",
                "Tìm kiếm {noun} ứng với số {val}",
                "Check {col_name} {val}",

                "Thông tin về {noun} số {val}",
                "{verb} {col_name} {val} là của ai?",
                "{verb} {noun} {val}",
                "Xem chi tiết {val}"
            ],

            "DIMENSION": [
                
                "Hãy liệt kê danh sách các {noun} có {col_name} là {val}",
                "Trích xuất báo cáo các {noun} thuộc loại {val}",
                "Lọc các {noun} đang ở trạng thái {val}",
                "Những {noun} nào là {val}?",
                "Cho xem danh sách {noun} {val}",
                "Tìm tất cả {noun} loại {val}",
                "Danh sách {val}"
            ],

            "METRIC": [
                
                "Thống kê tổng {col_metric} của các {noun} được phân loại theo {col_group} {val}",
                "Hãy tính toán tổng giá trị {col_metric} cho nhóm {val}",
                "Tổng {col_metric} của {noun} {val} là bao nhiêu?",

                "{noun} {val} có tổng {col_metric} là mấy?",
                "Cộng hết {col_metric} của các giao dịch {val}",
                "Tính tổng tiền {col_metric} theo {col_group} {val}"
            ],

            "TEMPORAL": [

                "Truy xuất lịch sử {noun} trong khoảng thời gian từ {start} đến {end}",
                "Liệt kê các giao dịch phát sinh từ ngày {start} tới ngày {end}",

                "Sao kê {noun} từ {start} - {end}",
                "Xem biến động {noun} giữa {start} và {end}",
                "Kiểm tra {noun} trong ngày {start}", 
                "Những {noun} nào diễn ra từ {start} đến {end}?",
                "Lịch sử {noun} {start} đến {end}"
            ],

            "MULTI_DIM_TIME": [
                
                "Lọc các {noun} {val} diễn ra từ {start} đến {end}",
                "Xem {noun} có {col_name} là {val} trong khoảng {start} - {end}",
                "Liệt kê {noun} {val} phát sinh ngày {start}",
                "Tìm {noun} {val} hôm {start}",
                "Sao kê {noun} loại {val} từ ngày {start} tới {end}"
            ],
            
            "COMPARISON": [
                "Tìm các {noun} có {col_metric} lớn hơn {val}",
                "Liệt kê {noun} với {col_metric} trên {val}",
                "Danh sách {noun} có {col_metric} nhỏ hơn {val}",
                "Lọc những {noun} có {col_metric} thấp hơn {val}"
            ],
            "RANKING": [
                "Top {k} {noun} có {col_metric} cao nhất",
                "Liệt kê {k} {noun} có {col_metric} lớn nhất",
                "Xem {k} {noun} có {col_metric} thấp nhất",
                "Những {noun} nào có {col_metric} cao nhất?"
            ],
            "AGGREGATION": [
                "Thống kê tổng {col_metric} theo từng {col_group}",
                "Tính tổng {col_metric} cho mỗi {col_group}",
                "Báo cáo {col_metric} phân theo {col_group}",
                "Xem doanh số {col_metric} dựa trên {col_group}"
            ],
            
            "FILTER_AND_GT": [ 
                "Tìm những {noun} có {dim_col} là {dim_val} và {met_col} lớn hơn {met_val}",
                "Liệt kê {noun} thuộc {dim_col} {dim_val} với {met_col} trên {met_val}",
                "Lọc {noun} {dim_val} có {met_col} > {met_val}",
                "Danh sách {noun} ({dim_col}: {dim_val}) có {met_col} cao hơn {met_val}"
            ],
            "FILTER_AND_LT": [ 
                "Tìm {noun} có {dim_col} {dim_val} và {met_col} dưới {met_val}",
                "Liệt kê {noun} {dim_val} nhưng {met_col} nhỏ hơn {met_val}",
                "Xem {noun} trạng thái {dim_val} có {met_col} thấp hơn {met_val}"
            ]
        }

    def get_templates(self, intent_code: str) -> List[str]:
        return self.templates.get(intent_code, [])

    def format_template(self, template_str: str, **kwargs) -> str:
        try:
            return template_str.format(**kwargs)
        except KeyError as e:
            return template_str 

if __name__ == "__main__":
    lib = GrammarLibrary()
    
    # Identity
    tpls = lib.get_templates("IDENTITY")
    print(f"--- Mẫu câu IDENTITY ({len(tpls)}) ---")
    print(lib.format_template(tpls[0], verb="Tra cứu", noun="giao dịch", col_name="mã tham chiếu", val="REF123"))

    # Multi-condition
    tpls_multi = lib.get_templates("MULTI_DIM_TIME")
    print(f"\n--- Mẫu câu ĐA ĐIỀU KIỆN ({len(tpls_multi)}) ---")
    print(lib.format_template(tpls_multi[0], noun="giao dịch", val="thất bại", start="01/01", end="31/01"))