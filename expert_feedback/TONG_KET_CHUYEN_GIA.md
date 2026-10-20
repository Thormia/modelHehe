# Tổng kết phiếu kiểm chứng dữ liệu với chuyên gia

**Phạm vi:** phiếu kiểm chứng **dữ liệu** của hệ thống, gồm 4 phần, mỗi phần 10 mẫu lấy ngẫu nhiên phân tầng:
- Dữ liệu fine-tune hội thoại thấu cảm.
- QA tự sinh (context RAG → câu trả lời chuyển từ đồng cảm sang gợi ý dinh dưỡng).
- Kho RAG dinh dưỡng.
- Kho RAG tâm lý.

6 người chấm từ 26/09 đến 13/10/2026 (R1–R6); 2 người chấm bổ sung ngày 18/10/2026 (R7, R8, chuyên môn Y khoa), cùng bộ mẫu.

Phiếu này **không** chấm câu trả lời của hệ thống final; phần đó nằm trong `BAO_CAO_DANH_GIA.md` và `chamtay_after_b3fix.md`.

**Cách tính:** `Hybrid-database-main/scripts/expert_agreement.py`, chạy lại được.
- Cách nhập điểm được chuẩn hoá ("4.0" → 4; "đạt"/"Đạt"/"pass" → đạt); ô trống được coi là thiếu và không tính.
- Ở hai phiếu bổ sung, 22 ô cột chọn được điền điểm 4–5 thay vì chọn từ danh sách: cột "Nhãn ontology_effect đúng" của cả 10 mẫu dinh dưỡng và cột "Dùng được để fine-tune" của mẫu FT-08, ở cả R7 và R8. Người chấm là bác sĩ, chấm theo nội dung; nhóm quy ước điểm 4–5 ở các cột này là Đạt/Đúng. Danh sách ô: `agreement.json`, khoá `choice_cells_from_score`.
- Các chỉ số đồng thuận được đối chiếu với thư viện chuẩn và cho kết quả trùng khớp: Fleiss' κ khớp ví dụ Wikipedia (0,210); Krippendorff's α và Gwet's AC1/AC2 khớp gói `krippendorff` 0.9.0 và `irrCAC` 0.4.4.
- Số liệu chi tiết: `expert_feedback/agreement.json`.

## Tóm tắt

- **Chất lượng dữ liệu được đánh giá cao:** điểm trung bình các tiêu chí từ 4,55 đến 4,92 trên thang 5; không có ô nào dưới 3.
  - QA tự sinh: an toàn y khoa Pass 80/80; không có mẫu nào cần chuyển tuyến mà chưa nói (0/79).
  - Dữ liệu fine-tune: "Dùng được để fine-tune" đạt 66/70 (94,3%).
  - Kho RAG dinh dưỡng: có 5/80 lượt chấm đánh dấu "phát biểu quá mức"; nhãn ontology đúng 69/70.
  - Kho RAG tâm lý: không có lỗi nào được đánh dấu ở cột chọn.
- **Độ đồng thuận cao nếu đo bằng chỉ số phù hợp với dữ liệu điểm dồn về phía cao:**
  - Điểm Likert: 97,1% các cặp người chấm lệch nhau không quá 1 điểm; Gwet's AC2 = 0,95.
  - Cột chọn: Fleiss' κ = 0,93; Krippendorff's α = 0,91; Gwet's AC1 = 0,94.
- **Fleiss' κ và Krippendorff's α trên điểm Likert gần 0.** Đây là nghịch lý kappa, không có nghĩa là người chấm bất đồng (giải thích ở mục 2.1).
- **Phát hiện cần xử lý cho hệ thống final:** món "Tiết lợn sống" (NUT_043), bị 2 chuyên gia cảnh báo nguy cơ nhiễm bệnh nguy hiểm và 2 chuyên gia khác đề xuất thay bằng nguồn sắt dễ tiếp cận hơn, vẫn có trong dữ liệu mà hệ thống đang dùng để gợi ý (mục 6).

8 người chấm, 40 mẫu (4 phần × 10 mẫu, cùng một bộ mẫu cho mọi người).

| Mã | File | Chuyên môn | Số ô đã chấm |
|---|---|---|---|
| R1 | BacSiDaKhoa | Bác sĩ đa khoa | 122/210 |
| R2 | CongNgheSinhHoc | Cử nhân công nghệ sinh học | 210/210 |
| R3 | HoaHuuCo | Công nghệ hóa hữu cơ và hóa dược | 210/210 |
| R4 | YHoc | Y học | 210/210 |
| R5 | Yhoc2 | Sinh viên Y dược | 210/210 |
| R6 | Yhoc3 | Y học | 210/210 |
| R7 | Yhoc4 | Y khoa (bổ sung 18/10) | 210/210 |
| R8 | Yhoc5 | Y khoa (bổ sung 18/10) | 209/210 |

## 1. Điểm theo tiêu chí

| Phần | Tiêu chí | n | Trung bình ± SD | Trung vị | Tỷ lệ ≥ 4 | Tỷ lệ = 5 | Thấp nhất |
|---|---|---|---|---|---|---|---|
| Dữ liệu fine-tune | Thấu cảm & công nhận cảm xúc | 80 | 4.67 ± 0.61 | 5 | 92% | 75% | 3 |
| Dữ liệu fine-tune | Tự nhiên, giọng người bạn | 70 | 4.66 ± 0.59 | 5 | 94% | 71% | 3 |
| Dữ liệu fine-tune | Chất lượng dịch tiếng Việt | 70 | 4.80 ± 0.40 | 5 | 100% | 80% | 4 |
| Dữ liệu fine-tune | An toàn | 80 | 4.89 ± 0.36 | 5 | 99% | 90% | 3 |
| QA tự sinh (RAG → gợi ý) | Thấu cảm & chuyển tiếp mượt | 80 | 4.79 ± 0.47 | 5 | 98% | 81% | 3 |
| QA tự sinh (RAG → gợi ý) | Lời khuyên dinh dưỡng đúng khoa học | 80 | 4.55 ± 0.53 | 5 | 99% | 56% | 3 |
| QA tự sinh (RAG → gợi ý) | Phù hợp triệu chứng | 80 | 4.59 ± 0.52 | 5 | 99% | 60% | 3 |
| QA tự sinh (RAG → gợi ý) | Trung thành với context | 80 | 4.71 ± 0.48 | 5 | 99% | 72% | 3 |
| Kho RAG dinh dưỡng | Thực phẩm giàu chất đã nêu | 80 | 4.64 ± 0.56 | 5 | 96% | 68% | 3 |
| Kho RAG dinh dưỡng | Cơ chế tác động đúng khoa học | 80 | 4.60 ± 0.52 | 5 | 99% | 61% | 3 |
| Kho RAG dinh dưỡng | Câu văn rõ ràng | 70 | 4.87 ± 0.34 | 5 | 100% | 87% | 4 |
| Kho RAG tâm lý | Nội dung đúng chuyên môn tâm lý | 76 | 4.92 ± 0.27 | 5 | 100% | 92% | 4 |
| Kho RAG tâm lý | Chất lượng dịch tiếng Việt | 70 | 4.64 ± 0.48 | 5 | 100% | 64% | 4 |
| Kho RAG tâm lý | Chunk đủ ngữ cảnh | 70 | 4.71 ± 0.46 | 5 | 100% | 71% | 4 |

| Phần | Tiêu chí (cột chọn) | n | Kết quả |
|---|---|---|---|
| Dữ liệu fine-tune | Dùng được để fine-tune (Đạt) | 70 | Đạt/Đúng/Pass: 66/70 (94.3%) |
| QA tự sinh (RAG → gợi ý) | An toàn y khoa (Pass) | 80 | Đạt/Đúng/Pass: 80/80 (100.0%) |
| QA tự sinh (RAG → gợi ý) | Cần chuyển tuyến mà chưa nói (Có) | 79 | Có: 0/79 (0.0%) |
| Kho RAG dinh dưỡng | Nhãn ontology_effect đúng | 70 | Đạt/Đúng/Pass: 69/70 (98.6%) |
| Kho RAG dinh dưỡng | Có phát biểu quá mức (Có) | 80 | Có: 5/80 (6.2%) |
| Kho RAG tâm lý | Nhãn target_mental_state đúng | 76 | Đạt/Đúng/Pass: 76/76 (100.0%) |
| Kho RAG tâm lý | Tags phù hợp | 70 | Đạt/Đúng/Pass: 70/70 (100.0%) |

## 2. Độ đồng thuận giữa người chấm

Đơn vị chấm = (mẫu, tiêu chí). Gộp theo phần vì mỗi tiêu chí chỉ có 10 mẫu.

| Phạm vi | Loại | Số đơn vị | Fleiss' κ (số mẫu đủ người chấm) | Krippendorff's α | Gwet's AC2/AC1 | Đồng ý hoàn toàn (cặp) | Lệch ≤ 1 điểm (cặp) |
|---|---|---|---|---|---|---|---|
| Dữ liệu fine-tune | Likert 1–5 | 40 | 0.03 (20) | 0.07 | 0.95 | 68.5% | 93.9% |
| Dữ liệu fine-tune | Cột chọn | 10 | – (0) | -0.05 | 0.87 | 88.6% | – |
| QA tự sinh (RAG → gợi ý) | Likert 1–5 | 40 | 0.02 (40) | 0.02 | 0.95 | 56.1% | 97.8% |
| QA tự sinh (RAG → gợi ý) | Cột chọn | 20 | 1.00 (19) | 1.00 | 1.00 | 100.0% | – |
| Kho RAG dinh dưỡng | Likert 1–5 | 30 | -0.05 (20) | 0.01 | 0.95 | 56.9% | 97.8% |
| Kho RAG dinh dưỡng | Cột chọn | 20 | -0.07 (10) | 0.84 | 0.85 | 91.6% | – |
| Kho RAG tâm lý | Likert 1–5 | 30 | -0.01 (6) | 0.10 | 0.97 | 67.9% | 100.0% |
| Kho RAG tâm lý | Cột chọn | 20 | – (6) | – | 1.00 | 100.0% | – |
| Tất cả | Likert 1–5 | 140 | 0.04 (86) | 0.05 | 0.95 | 61.9% | 97.1% |
| Tất cả | Cột chọn | 70 | 0.93 (35) | 0.91 | 0.94 | 96.2% | – |

### 2.1 Cách đọc các chỉ số đồng thuận

- **Fleiss' κ và Krippendorff's α** so mức đồng ý thực tế với mức đồng ý "do may rủi". Mức may rủi này được tính từ phân bố điểm chung của mọi người chấm.
  - Ở đây 92–100% điểm là 4 hoặc 5 (tùy tiêu chí), nên mức may rủi đã rất cao. Hai người cùng cho 5 điểm gần như không được tính công, và một lần lệch 4–5 bị phạt nặng.
  - Vì vậy κ và α xấp xỉ 0, dù 97% các cặp người chấm lệch nhau không quá 1 điểm. Hiện tượng này là **nghịch lý kappa** (Feinstein & Cicchetti, 1990), thường gặp khi chất lượng mẫu đồng đều ở mức cao.
- **Gwet's AC1/AC2** (Gwet, 2008) tính mức may rủi theo cách khác, nên ổn định khi điểm dồn về một phía. Báo cáo dùng AC2 với trọng số bậc hai cho thang Likert, AC1 cho cột chọn, kèm **tỷ lệ đồng ý thô**. Đây là các chỉ số chính.
- **Fleiss' κ vẫn được báo cáo** theo kế hoạch trong `idea.docx`:
  - Chỉ tính trên các mẫu có đủ 8 người chấm (số mẫu ghi trong ngoặc). R1 bỏ trống một số tiêu chí nên có phần chỉ còn ít mẫu.
  - Khi một phần có mọi người chấm cùng một giá trị (ví dụ Tags phù hợp: tất cả "Đúng"), κ và α không xác định được, bảng ghi "–", nhưng đồng ý thô là 100%.
- Mỗi tiêu chí chỉ có 10 mẫu, nên chỉ số theo từng tiêu chí dao động mạnh. Bảng chính gộp theo phần.
- Mức đánh giá theo Landis & Koch (dùng chung cho κ, α, AC): trên 0,80 là gần như hoàn toàn; 0,61–0,80 là đáng kể.
  - Likert: AC2 = 0,95–0,97 ở mọi phần.
  - Cột chọn: AC1 = 0,85–1,00.

### Theo từng tiêu chí Likert (10 mẫu mỗi tiêu chí, chỉ để tham khảo)

| Phần | Tiêu chí | Krippendorff's α | Gwet's AC2 | Đồng ý hoàn toàn | Lệch ≤ 1 |
|---|---|---|---|---|---|
| Dữ liệu fine-tune | Thấu cảm & công nhận cảm xúc | -0.01 | 0.92 | 59% | 88% |
| Dữ liệu fine-tune | Tự nhiên, giọng người bạn | 0.07 | 0.93 | 61% | 90% |
| Dữ liệu fine-tune | Chất lượng dịch tiếng Việt | 0.06 | 0.97 | 70% | 100% |
| Dữ liệu fine-tune | An toàn | 0.06 | 0.98 | 82% | 98% |
| QA tự sinh (RAG → gợi ý) | Thấu cảm & chuyển tiếp mượt | -0.06 | 0.96 | 67% | 95% |
| QA tự sinh (RAG → gợi ý) | Lời khuyên dinh dưỡng đúng khoa học | -0.05 | 0.93 | 46% | 99% |
| QA tự sinh (RAG → gợi ý) | Phù hợp triệu chứng | 0.06 | 0.94 | 53% | 99% |
| QA tự sinh (RAG → gợi ý) | Trung thành với context | -0.03 | 0.95 | 58% | 98% |
| Kho RAG dinh dưỡng | Thực phẩm giàu chất đã nêu | -0.02 | 0.93 | 51% | 95% |
| Kho RAG dinh dưỡng | Cơ chế tác động đúng khoa học | -0.04 | 0.94 | 49% | 99% |
| Kho RAG dinh dưỡng | Câu văn rõ ràng | -0.09 | 0.98 | 75% | 100% |
| Kho RAG tâm lý | Nội dung đúng chuyên môn tâm lý | -0.02 | 0.99 | 85% | 100% |
| Kho RAG tâm lý | Chất lượng dịch tiếng Việt | -0.00 | 0.95 | 53% | 100% |
| Kho RAG tâm lý | Chunk đủ ngữ cảnh | 0.08 | 0.96 | 62% | 100% |

## 3. Mức độ chấm của từng người (Likert, mọi phần)

| Mã | Trung bình | Tỷ lệ cho 5 điểm | Số ô Likert đã chấm |
|---|---|---|---|
| R1 | 4.98 | 98% | 86 |
| R2 | 4.52 | 52% | 140 |
| R3 | 4.88 | 88% | 140 |
| R4 | 4.81 | 81% | 140 |
| R5 | 4.73 | 76% | 140 |
| R6 | 4.59 | 70% | 140 |
| R7 | 4.66 | 66% | 140 |
| R8 | 4.66 | 66% | 140 |

## 4. Mẫu có điểm trung bình thấp nhất (Likert, trung bình mọi tiêu chí và người chấm)

| Mẫu | Trung bình | Số nhận xét |
|---|---|---|
| GEN-10 | 4.50 | 3 |
| NUT-02 | 4.52 | 3 |
| GEN-01 | 4.53 | 6 |
| GEN-04 | 4.53 | 3 |
| NUT-01 | 4.57 | 4 |
| NUT-03 | 4.57 | 0 |
| GEN-08 | 4.59 | 3 |
| FT-01 | 4.63 | 2 |


## 5. Nhận xét định tính của chuyên gia (tổng hợp theo chủ đề)

### Dữ liệu fine-tune (chủ yếu từ R6; R1 góp ý FT-01, FT-05)
- **Vội chuyển sang tích cực, phủ nhận cảm xúc:**
  - Câu trả lời công nhận cảm xúc rồi lập tức "Nhưng…", "Tuy nhiên…" để kéo sang góc nhìn tích cực (FT-01, FT-07, FT-10).
  - Người dùng dễ thấy nỗi đau của mình chưa được lắng nghe.
- **Phán xét, giọng bài giảng:**
  - Dán nhãn hành vi là "không lành mạnh" (uống rượu ở FT-04; nhịn ăn ở FT-08).
  - Giọng văn lý thuyết, xa cách (FT-06, FT-10).
- **Thiếu câu hỏi gợi mở,** câu trả lời khép lại vấn đề (FT-03, FT-09).
- **Rủi ro an toàn ở FT-08:** khuyên tập thể dục cho người đang nhịn ăn, có thể gây hạ đường huyết và kích hoạt hành vi tập luyện cưỡng chế ở người rối loạn ăn uống.
- 4 mẫu bị chấm "Không đạt" để fine-tune: FT-04, FT-07, FT-08, FT-10, đều do R6 chấm. Các người chấm khác, kể cả R7 và R8, cho các mẫu này Đạt, nên đây là điểm cần nhóm xem lại.
- R6 đề xuất câu trả lời viết lại cho FT-01 đến FT-10 (xem file của R6), có thể dùng làm tham khảo khi làm phiên bản dữ liệu sau.

### QA tự sinh (R3, R4, R5, R6, R7, R8)
- **Phóng đại tác dụng của dưỡng chất (góp ý nhiều nhất):**
  - Selen trong nấm mỡ được khẳng định là "kìm hãm căng thẳng, giúp dịu lại", trong khi bằng chứng chủ yếu đến từ nghiên cứu trên chuột hoặc tế bào (GEN-01, GEN-08). R7 nói thêm: chưa thể quy mệt mỏi cho thiếu selen chỉ qua triệu chứng; bổ sung selen chỉ hỗ trợ một phần, cần phối hợp cách khác.
  - Rong biển được nói là "giàu vitamin C", nhưng thực tế hàm lượng thấp và vitamin C bị phân huỷ khi nấu (GEN-04).
  - Khoai môn được gắn với "Thiamin (B1)", trong khi B6 mới là dưỡng chất nổi bật (GEN-05).
  - Sắt chỉ cải thiện tâm trạng khi cơ thể đang thiếu sắt (GEN-02, GEN-10).
  - Đề xuất chung: viết mềm hơn ("một trong những nguồn", "có thể hỗ trợ").
- **Chọn thực phẩm phổ biến trong tư vấn y khoa (R7, R8):**
  - Nguồn sắt nên là thịt đỏ, rau xanh đậm thay vì hến (GEN-02); có thực phẩm giàu sắt hơn và ít hại sức khoẻ hơn đường cát (GEN-06).
  - Vitamin C: ổi giàu hơn và dễ mua hơn kiwi (GEN-03); nên dùng trái cây giàu vitamin C (GEN-10).
  - Nên đổi sang thực phẩm dễ tiếp cận hơn (GEN-01).
- **Tính thực tế:** gợi ý món cầu kỳ (cơm cuộn rong biển, dạ dày bò xào) cho người đang kiệt sức hoặc thiếu thời gian (GEN-04, GEN-08).
- **Lưu ý chế biến và đối tượng:**
  - Người lạnh bụng ăn nhiều nấm có thể khó tiêu (GEN-01).
  - Vi sinh vật có lợi trong miso nhạy với nhiệt (GEN-07).
  - Không nên ăn sát giờ ngủ (GEN-08).
  - Cần ghi rõ "sắn khô" là loại nào (GEN-10).
- **Giọng điệu:** dùng từ "phiền toái" cho cơn lo âu là xem nhẹ cảm xúc; chuyển ý sang món chè đột ngột (GEN-09).
- **Định lượng (R7):** đề nghị nêu lượng ăn cụ thể và mức an toàn (GEN-02, GEN-03). Hệ thống chủ ý không nêu định lượng (guardrail chặn số mg, g, kcal) để tránh tư vấn liều, nên đề xuất này không áp dụng cho câu trả lời của hệ thống.

### Kho RAG dinh dưỡng (R3, R4, R5, R6, R7, R8)
- **NUT-01 Tiết lợn sống:** nguy cơ nhiễm vi khuẩn và virus gây bệnh nguy hiểm, "không nên khuyến nghị" (R4, R5). R7 và R8 đề xuất thay bằng nguồn sắt dễ tiếp cận như thịt đỏ, rau củ giàu sắt.
- NUT-02 Lá mơ lông: thực tế chỉ ăn vài gram làm rau gia vị, nên lượng vitamin C nạp vào không đáng kể. R7, R8: ổi, kiwi, rau xanh đậm giàu vitamin C và dễ ăn hơn.
- NUT-04 Cà rốt: không phải nguồn kẽm nổi bật (khoảng 0,2 mg/100 g); vi chất nổi bật là beta-caroten.
- NUT-06 Cà muối nén: rất mặn; dễ hiểu nhầm là nên ăn nhiều, gây hại cho huyết áp và dạ dày (R3, R6). R7: có thể dùng thêm sữa chứa vi khuẩn có lợi cho tiêu hoá.
- NUT-08 Trà Ô long: nhãn ontology (digestion) không khớp với phần giải thích (trầm cảm). Đây là lượt duy nhất nhãn bị chấm "Sai". R7, R8: chứa caffeine, cần lưu ý hoặc thay món với người rối loạn giấc ngủ.

### Kho RAG tâm lý
- Mọi nhãn trạng thái tâm lý và tags được chấm "Đúng".
- R7 góp ý PSY-01: nội dung và nhãn có thể nhầm lẫn về định nghĩa trầm cảm (Depression), nên xem lại nhãn hoặc nội dung; PSY-02: bản dịch khó hiểu nếu không có tình huống cụ thể.

## 6. Liên hệ với hệ thống final và việc cần nhóm quyết định

Kiểm tra đối chiếu với `data/processed/400 data dinh duong.json` và `state_effect_map.json` (danh sách loại trừ hiện chỉ có `NUT_060`):

| Góp ý | Món trong dữ liệu hệ thống | Trạng thái hiện tại | Đề xuất |
|---|---|---|---|
| Tiết lợn sống: nguy cơ nhiễm bệnh; nên thay nguồn sắt khác | NUT_043 "Tiết lợn sống" (mood_regulation) | **Vẫn được gợi ý** | Thêm vào `excluded_foods` (chỉ là cấu hình, không sửa dữ liệu) |
| Cà muối nén: rất mặn | NUT_215 "Cà muối nén", NUT_346 "Cà muối sối" (mood_regulation) | Vẫn được gợi ý | Cân nhắc loại, hoặc giữ nhưng nêu lưu ý ăn ít |
| Cà rốt không giàu kẽm | NUT_147 (ontology_effect trống) | Không được gợi ý (không có đích tác động) | Không cần làm gì cho hệ thống |
| Trà Ô long: nhãn lệch; chứa caffeine | NUT_359 (digestion) | Vẫn được gợi ý | Nhóm xem lại nhãn và lưu ý caffeine |

Ngoài phạm vi phiếu chấm, mình thấy trong dữ liệu còn **NUT_113 "Lá sắn tươi"**. Lá sắn tươi có độc tố cyanogenic, cần nấu kỹ mới ăn được, nên nhóm nên xem cùng lúc với NUT_043.

**Mọi thay đổi ở trên đều thay đổi hệ thống sau lần chạy final.** Nếu nhóm loại món, kết quả final (chạy 16–17/10) vẫn giữ nguyên làm số chính thức. Báo cáo sẽ ghi rõ là đã loại món sau khi có góp ý của chuyên gia. Bộ test crisis và safety không đi vào nhánh gợi ý món, nên các số đó không bị ảnh hưởng.

## 7. Hạn chế của đợt kiểm chứng
- Chỉ có 40 mẫu, mỗi tiêu chí 10 mẫu, nên khoảng tin cậy rộng.
- Thành phần người chấm không đồng đều về chuyên môn (theo tên file và thông tin trong phiếu): 1 bác sĩ đa khoa, 5 người ngành y (1 người ghi là sinh viên Y dược), 1 người công nghệ sinh học, 1 người hoá dược. Không có chuyên gia tâm lý lâm sàng và không có chuyên gia dinh dưỡng chuyên ngành.
- R1 bỏ trống 88/210 ô và không ghi lý do (phiếu hướng dẫn để trống khi nằm ngoài chuyên môn). Vì vậy Fleiss' κ (chỉ tính mẫu đủ người chấm) ở một số phần chỉ còn 6–20 mẫu.
- 22 ô cột chọn của R7, R8 được quy đổi từ điểm 4–5 thành Đạt/Đúng theo quy ước của nhóm (mục đầu).
- Mức chấm giữa các người chấm khác nhau rõ: R1 cho 98% điểm 5, R2 chỉ 52% (mục 3). Một phần nguyên nhân là điểm dồn về phía cao.
- Phiếu yêu cầu chấm độc lập, nhưng nhóm không có cách kiểm chứng điều này.
