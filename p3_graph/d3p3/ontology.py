"""Ontology D3 – P3.1.

Chuỗi phụ thuộc: Cảm biến -> Máy -> Công đoạn -> Linh kiện -> Sản phẩm -> Đơn hàng.
Mọi module khác (P1 backward, P4 risk, P5 dashboard) chỉ nên dùng các hằng số ở đây
thay vì gõ chuỗi tự do.
"""

# ---- Loại node --------------------------------------------------------------
SENSOR = "sensor"
MACHINE = "machine"
PROCESS = "process"
COMPONENT = "component"
PRODUCT = "product"
ORDER = "order"

NODE_TYPES = [SENSOR, MACHINE, PROCESS, COMPONENT, PRODUCT, ORDER]
LAYER = {t: i for i, t in enumerate(NODE_TYPES)}  # 0..5
VN_NAME = {
    SENSOR: "Cảm biến", MACHINE: "Máy", PROCESS: "Công đoạn",
    COMPONENT: "Linh kiện", PRODUCT: "Sản phẩm", ORDER: "Đơn hàng",
}
# Các tầng được đánh giá trong truy vết xuôi (E1)
IMPACT_LAYERS = [PROCESS, COMPONENT, PRODUCT, ORDER]

# ---- Loại cạnh (luôn hướng từ thượng nguồn -> hạ nguồn) ---------------------
MONITORS = "monitors"        # Sensor -> Machine | Sensor -> Process (nhánh B)
OPERATES_IN = "operates_in"  # Machine -> Process   weight = tỷ trọng tải của máy trong công đoạn
FEEDS = "feeds"              # Process -> Process   weight = mức phụ thuộc vào công đoạn trước
PRODUCES = "produces"        # Process -> Component weight = tỷ trọng linh kiện do công đoạn làm ra
USED_IN = "used_in"          # Component -> Product weight = mức trọng yếu của linh kiện trong SP
FULFILLS = "fulfills"        # Product -> Order     weight = tỷ trọng SP trong đơn hàng

EDGE_TYPES = {
    MONITORS: (SENSOR, (MACHINE, PROCESS)),
    OPERATES_IN: (MACHINE, (PROCESS,)),
    FEEDS: (PROCESS, (PROCESS,)),
    PRODUCES: (PROCESS, (COMPONENT,)),
    USED_IN: (COMPONENT, (PRODUCT,)),
    FULFILLS: (PRODUCT, (ORDER,)),
}
# Cạnh tham gia lan truyền tác động (monitors chỉ là quan hệ quan sát)
PROPAGATION_EDGES = [OPERATES_IN, FEEDS, PRODUCES, USED_IN, FULFILLS]

# ---- Nhánh dữ liệu ----------------------------------------------------------
BRANCH_A = "A"        # node Máy gắn bản ghi AI4I 2020
BRANCH_B = "B"        # node Công đoạn gắn bản ghi SECOM
SHARED = "shared"     # linh kiện/sản phẩm/đơn hàng dùng chung

DOMAIN_AI4I = "ai4i"
DOMAIN_SECOM = "secom"
# Loại node mang dữ liệu thật (= nguồn sự cố) theo domain
SOURCE_TYPE = {DOMAIN_AI4I: MACHINE, DOMAIN_SECOM: PROCESS}
SOURCE_BRANCH = {DOMAIN_AI4I: BRANCH_A, DOMAIN_SECOM: BRANCH_B}

# ---- Chế độ lỗi -> nhóm nguyên nhân nghi ngờ (mục 5.3) -----------------------
FAILURE_MODES_AI4I = ["TWF", "HDF", "PWF", "OSF", "RNF"]
CAUSE_GROUP = {
    "TWF": "Mòn dao cụ",
    "HDF": "Tản nhiệt kém",
    "PWF": "Nguồn / công suất",
    "OSF": "Quá tải cơ khí",
    "RNF": "Ngẫu nhiên (không quan sát được)",
    "UNK": "Chưa xác định",
    "SECOM_FAIL": "Thông số quy trình bán dẫn",
}
