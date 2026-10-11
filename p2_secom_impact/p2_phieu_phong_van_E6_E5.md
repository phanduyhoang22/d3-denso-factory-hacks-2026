# Phiếu P2.8 – phỏng vấn kỹ sư (E6) và chấm khuyến nghị (E5)

Việc của con người, không tự động hóa được. Phiếu này giúp thu thập số liệu đúng định dạng để điền vào báo cáo (E6, E5) và hiệu chỉnh các tham số giả lập (`CFG`, `EXP`).

## A. Phỏng vấn 1–2 kỹ sư (E6: thời gian điều tra thủ công)

Ghi rõ nguồn con số (tên, vai trò, ngày) vì đây là ước tính, không phải đo đạc.

| # | Câu hỏi | Trả lời | Dùng cho |
|---|---|---|---|
| 1 | Khi một máy báo bất thường, mất bao lâu để biết công đoạn/linh kiện/sản phẩm/đơn hàng nào bị ảnh hưởng? (phút, theo ca thường/ca phức tạp) | | E6: thời gian xác định đối tượng bị ảnh hưởng |
| 2 | Mất bao lâu để xác định nguyên nhân có khả năng nhất? Dùng những nguồn dữ liệu nào (PLC, QC, bảo trì, kho)? | | E6: thời gian điều tra |
| 3 | Dữ liệu quan hệ giữa máy, công đoạn, linh kiện, sản phẩm, đơn hàng được ghi ở đâu? Đầy đủ khoảng bao nhiêu %? | | E4: mức thiếu cạnh thực tế |
| 4 | Thời gian dừng điển hình theo từng loại lỗi (mòn dao, tản nhiệt, nguồn, quá tải) là bao nhiêu phút? | | `CFG["downtime_min"]` |
| 5 | Máy nào thay thế được máy nào, và gánh được bao nhiêu % tải? | | `substitute_share` |
| 6 | Tồn kho/đệm giữa các công đoạn thường đủ cho bao nhiêu phút sản xuất? | | `buf_range`, `raw_buf_range` |
| 7 | Đơn hàng thường có dư thời gian (slack) bao lâu trước hạn? Độ ưu tiên được quyết định thế nào? | | `slack_mean_min`, `priority_p` |
| 8 | Bộ phận nào chịu trách nhiệm từng loại đối tượng? | | `DEPT_OF_TYPE` |
| 9 | Hiện có bao nhiêu sự cố/tháng, và bao nhiêu % gây trễ đơn hàng? | | Ước lượng ROI |

Tóm tắt E6 (điền sau khi phỏng vấn): thời gian thủ công ước tính = ___ phút (nguồn: ___). Pipeline P2 chạy khoảng 1 ms mỗi sự cố (cột `runtime_ms`, chỉ phần truy vết và chấm điểm).

## B. Phiếu chấm E5 (khuyến nghị hành động có hợp lý không)

Mỗi thành viên chấm độc lập 10–15 kịch bản từ `p2_scenario_*.json` và bảng hành động của P3. Mỗi dòng: Đúng / Sai / Không chắc.

| Kịch bản (seed/UDI) | Nguyên nhân xếp đầu hợp lý? | Phạm vi ảnh hưởng hợp lý? | Hành động hợp lý và làm được? | Người chấm | Ghi chú |
|---|---|---|---|---|---|
| | | | | | |

Tổng hợp E5: số kịch bản đúng / tổng = ___ (ghi rõ có ít nhất 2 người chấm và mức đồng thuận).
