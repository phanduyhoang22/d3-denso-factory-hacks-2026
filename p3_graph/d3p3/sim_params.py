"""Tất cả tham số MÔ PHỎNG của P3 (mục 18.1: phải ghi rõ là tự sinh).

AI4I/SECOM chỉ cung cấp tín hiệu cảm biến + nhãn lỗi. Mọi thứ dưới đây (cấu trúc
đồ thị, trọng số, tồn kho, ưu tiên, hạn giao, máy thay thế, mức nghiêm trọng) là
giả định minh họa và được tài liệu hóa trong docs/sim_params.md.
"""

# ---- Quy mô đồ thị (generate_graph(seed, size)) -----------------------------
SIZES = {
    #            lines A, procs/line A, lines B, procs/line B, products, orders
    "small":  dict(lines_a=2, procs_a=3, lines_b=2, procs_b=3, n_products=6,  n_orders=15),
    "medium": dict(lines_a=3, procs_a=4, lines_b=2, procs_b=4, n_products=12, n_orders=40),
    "large":  dict(lines_a=5, procs_a=5, lines_b=3, procs_b=5, n_products=28, n_orders=100),
}

# ---- Cấu trúc ---------------------------------------------------------------
MACHINES_PER_PROCESS_A = (1, 3)      # số máy / công đoạn nhánh A (đều, gồm 2 đầu)
MACHINES_PER_PROCESS_B = (1, 2)      # nhánh B (không gắn dữ liệu, chỉ cho đủ ontology)
P_SHARED_MACHINE = 0.15              # xác suất 1 máy phục vụ thêm công đoạn kế tiếp
P_FEED = 0.6                         # xác suất công đoạn i nối "feeds" sang i+1 trong line
FEED_WEIGHT = (0.3, 0.7)
COMPONENTS_PER_PROCESS = (1, 3)
P_DUAL_SOURCE = 0.2                  # linh kiện có 2 công đoạn cùng sản xuất
PRODUCE_WEIGHT = (0.6, 1.0)
COMPONENTS_PER_PRODUCT = (2, 5)
USED_IN_WEIGHT = (0.3, 1.0)          # mức trọng yếu
P_HOME_LINE_COMPONENT = 0.8          # SP thuộc 1 "họ" gắn với 1 line: 80% linh kiện từ line nhà
P_SAME_FAMILY_ORDER = 0.7            # SP thứ 2,3 trong đơn hàng cùng họ với SP đầu (xác suất)
PRODUCTS_PER_ORDER = (1, 3)
MACHINE_TYPE_MIX = {"L": 0.6, "M": 0.3, "H": 0.1}   # theo tỷ lệ Type trong AI4I
SECOM_SENSOR_GROUPS = 3              # 590 cảm biến SECOM gom thành 3 node nhóm/công đoạn
AI4I_SENSORS = ["air_temp", "process_temp", "rot_speed", "torque", "tool_wear"]

# ---- Thuộc tính vận hành ----------------------------------------------------
SPARE_CAPACITY = (0.0, 0.5)          # công suất dư của máy (cho máy thay thế, P4 dùng)
WIP_BUFFER = (0.0, 0.2)              # bộ đệm bán thành phẩm của công đoạn – ẨN với hệ thống
DAILY_USAGE = (50, 500)              # linh kiện/ngày
STOCK_COVER_DAYS = (0.0, 6.0)        # số ngày tồn kho dự phòng
LEAD_TIME_DAYS = (2, 14)
N_ALT_SOURCES = (0, 3)
BUFFER_CAP = 0.7                     # tồn kho hấp thụ tối đa 70% cú sốc
ORDER_PRIORITY = {1: 0.2, 2: 0.5, 3: 0.3}            # 1 = thấp, 3 = cao (xác suất)
DUE_IN_DAYS = (1, 30)
ORDER_QTY = (100, 5000)

# ---- Mức nghiêm trọng thật theo chế độ lỗi (đầu vào lan truyền) --------------
SEVERITY_BY_MODE = {"PWF": 1.0, "HDF": 0.9, "OSF": 0.8, "TWF": 0.6,
                    "RNF": 0.5, "UNK": 0.7, "SECOM_FAIL": 0.8}

# ---- Ground truth & quan sát -----------------------------------------------
IMPACT_THRESHOLD = 0.10              # đối tượng "bị ảnh hưởng thật" nếu true_impact >= 0.10
WEIGHT_NOISE_SIGMA = 0.25            # nhiễu log-normal trên trọng số cạnh hệ thống nhìn thấy
STOCK_NOISE_SIGMA = 0.20             # nhiễu log-normal trên tồn kho hệ thống nhìn thấy
EDGE_DROP_RATES = [0.0, 0.10, 0.25, 0.50]
CONFOUNDER_RATES = [0.0, 0.25, 0.50]

# ---- Dòng thời gian kịch bản (timestamp GIẢ) --------------------------------
SCENARIO_BASE_TIME = "2026-09-15T08:00:00"
ROOT_OFFSET_H = (0.0, 2.0)           # sự cố gốc trong 2h đầu
OUTCOME_LAG_H = (2.0, 6.0)           # kết quả xấu xuất hiện sau sự cố gốc 2–6h
CONFOUNDER_WINDOW_BEFORE_ROOT_H = 3.0

# ---- Chia dữ liệu ----------------------------------------------------------
TEST_FRACTION = 0.30                 # AI4I: ngẫu nhiên phân tầng; SECOM: 30% cuối theo thời gian
DATA_SPLIT_SEED = 2020               # cố định để mọi người dùng chung 1 cách chia
