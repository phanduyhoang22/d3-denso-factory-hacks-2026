# Dàn ý slide 7 mục (P5 ghép; mỗi người nộp phần của mình cho P5 vào ngày 9)

Căn cứ: yêu cầu bài nộp trên densohackathon.vn ("Presentation Deck: solution overview, business context, vision and
objectives, market and research analysis, technical design, alignment with the competition themes") và tiêu chí
chấm vòng sơ loại (đầy đủ, đổi mới và khả thi, rõ ràng, bám đề).

| # | Mục | Nội dung chính | Người soạn | Số slide |
|---|---|---|---|---|
| 1 | **Bối cảnh & vấn đề** | 4 vấn đề ở mục 1 (dữ liệu phân tán, phát hiện cục bộ, truy vết thủ công, khó đánh giá mức độ). Một câu chuyện thực tế: "máy rung, ai biết đơn nào trễ?" | P4 | 1–2 |
| 2 | **Bám đề D3 & phạm vi** | Trích đề D3. Lý do chọn **sự cố thiết bị** làm điểm vào. Bảng đối chiếu 3 yêu cầu D3 (mô hình liên kết, engine lan truyền, hành động theo bộ phận) với các module của nhóm. Hướng mở rộng sang biến động nguyên liệu và đơn hàng | P5 | 1–2 |
| 3 | **Giải pháp & tầm nhìn** | 4 câu hỏi: chuyện gì, tại sao, ảnh hưởng gì, làm gì trước. Luồng Phát hiện → Truy vết → Đánh giá → Ưu tiên → Hành động. Bảng "cách thông thường vs đề xuất" (mục 12) | P5 | 1–2 |
| 4 | **Thiết kế kỹ thuật** | Kiến trúc 6 tầng ↔ 3 tầng của Xin Chunhua 2025. Pipeline 5 mô-đun (mục 16.1). Ontology và đồ thị. Ý tưởng từ CN112152830B (fault tracing graph, KB kèm adoption rate, vòng phản hồi) | P1 (phát hiện), P3 (đồ thị/truy vết), P4 (rủi ro/hành động) | 3–4 |
| 5 | **Demo** | Ảnh chụp dashboard 5 bước trên một sự cố thật (vd OSF ở nhánh AI4I): máy → lô linh kiện → sản phẩm → đơn hàng. Có video dự phòng nếu demo trực tiếp lỗi | P5 | 1–2 |
| 6 | **Thí nghiệm & kết quả** | Dữ liệu: AI4I và SECOM thật, đồ thị mô phỏng có ground truth. Kết quả E0–E4 so với baseline (mean ± std). **E4: hiệu năng khi thiếu 25–50% cạnh.** E6: thời gian pipeline so với điều tra thủ công. Các hạn chế nêu thẳng (mục 18.6) | P2 (biểu đồ), P4 (kết luận) | 2–3 |
| 7 | **Giá trị, thị trường & lộ trình** | Giá trị vận hành (thời gian điều tra, dừng máy, đơn trễ). Sản phẩm tương tự (Datagrand fault KG…) và điểm khác biệt. Lộ trình 3 tháng: dữ liệu Denso thật → GNN, nhân quả, realtime | P4 + P5 | 1–2 |

## Lưu ý trình bày
- Mọi thuộc tính nghiệp vụ trong demo (tồn kho, hạn giao, trọng số) phải ghi chú là **tham số mô phỏng**.
- Nói "nguyên nhân **khả dĩ**", không nói "nguyên nhân".
- SECOM trình bày là **kiểm tra pipeline dùng được cho domain khác**, không phải dữ liệu nhà máy Denso.
- Mỗi con số kết quả ghi kèm số seed và ghi là ± std.
