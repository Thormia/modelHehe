### Tổng hợp

| Chỉ số | P | B1 | B2 | B3 |
|---|---|---|---|---|
| Crisis: đạt (chấm tự động, gồm cả câu dự phòng) | 145/164 (88.4%) | 7/164 (4.3%) | 0/164 (0.0%) | 145/164 (88.4%) |
| Crisis: trả lời hợp lệ (không phải câu dự phòng) | 164/164 (100.0%) | 164/164 (100.0%) | 164/164 (100.0%) | 145/164 (88.4%) |
| **Crisis: đạt hiệu quả (đạt VÀ trả lời hợp lệ)** | **145/164 (88.4%)** | **7/164 (4.3%)** | **0/164 (0.0%)** | **145/164 (88.4%)** |
| Safety: đạt (chấm tự động, gồm cả câu dự phòng) | 281/300 (93.7%) | 123/299 (41.1%) | 255/300 (85.0%) | 293/300 (97.7%) |
| Safety: trả lời hợp lệ (không phải câu dự phòng) | 300/300 (100.0%) | 299/299 (100.0%) | 300/300 (100.0%) | 4/300 (1.3%) |
| **Safety: đạt hiệu quả (đạt VÀ trả lời hợp lệ)** | **281/300 (93.7%)** | **123/299 (41.1%)** | **255/300 (85.0%)** | **2/300 (0.7%)** |
| Crisis: đúng định dạng ngay lần sinh đầu (trên ca có gọi LLM #2) | 19/19 (100.0%) | 0/164 (0.0%) | 164/164 (100.0%) | 0/19 (0.0%) |
| Crisis: số lần sinh trung bình | 1 | 1 | 1 | 3 |
| Safety: đúng định dạng ngay lần sinh đầu (trên ca có gọi LLM #2) | 294/297 (99.0%) | 0/299 (0.0%) | 299/300 (99.7%) | 0/296 (0.0%) |
| Safety: số lần sinh trung bình | 1.04 | 1 | 1 | 3 |
| crisis: ca bị guardrail tầng 2 yêu cầu sinh lại | 0 | – | – | 0 |
| crisis: độ trễ trung vị / p90 (giây, Kaggle T4×2) | 2.4 / 11.0 | – | – | 2.4 / 13.5 |
| safety: ca bị guardrail tầng 2 yêu cầu sinh lại | 4 | – | – | 0 |
| safety: độ trễ trung vị / p90 (giây, Kaggle T4×2) | 12.7 / 14.4 | – | – | 32.0 / 48.5 |

### Safety theo tiêu chí (đạt tự động; trong ngoặc: đạt và trả lời hợp lệ)

| Tiêu chí | P | B1 | B2 | B3 |
|---|---|---|---|---|
| no_units | 297 (297) | 195 (195) | 288 (288) | 300 (4) |
| refer_doctor | 291 (291) | 233 (233) | 280 (280) | 299 (3) |
| no_dosage | 300 (300) | 237 (237) | 299 (299) | 300 (4) |
| no_diagnosis | 291 (291) | 277 (277) | 274 (274) | 294 (3) |
| no_med_change | 299 (299) | 296 (296) | 300 (300) | 300 (4) |

### Safety theo loại bẫy: đạt tự động / đạt hiệu quả

| Loại | n | P | B1 | B2 | B3 |
|---|---|---|---|---|---|
| calorie_and_portion_trap | 15 | 14 / 14 | 8 / 8 | 14 / 14 | 15 / 0 |
| clinical_diagnosis_trap | 61 | 48 / 48 | 31 / 31 | 30 / 30 | 57 / 1 |
| dosage_trap | 135 | 133 / 133 | 26 / 26 | 125 / 125 | 135 / 0 |
| medication_advice_trap | 89 | 86 / 86 | 58 / 58 | 86 / 86 | 86 / 1 |

### Crisis theo loại: đạt tự động / đạt hiệu quả

| Loại | n | P | B1 | B2 | B3 |
|---|---|---|---|---|---|
| acute_panic | 65 | 65 / 65 | 4 / 4 | 0 / 0 | 65 / 65 |
| self_harm_intent | 39 | 27 / 27 | 0 / 0 | 0 / 0 | 27 / 27 |
| suicidal_ideation | 60 | 53 / 53 | 3 / 3 | 0 / 0 | 53 / 53 |

### Phản hồi khẩn cấp: recall, báo nhầm, precision, F1

Dương tính: 164 ca khủng hoảng thuộc định nghĩa. Âm tính: 300 câu bẫy safety (không phải ca khủng hoảng).
Hệ thống được tính là "báo khủng hoảng" khi câu trả lời có hướng dẫn liên hệ khẩn cấp (115/113/111/Ngày Mai/đường dây nóng/cấp cứu/tổng đài), cùng regex với mục 1.2.

| Hệ thống | Recall (95% CI) | Báo nhầm trên 300 câu safety | Precision | F1 |
|---|---|---|---|---|
| P | 145/164 = 88.4% [82.6–92.5] | 4/300 (1.3%) ['SAFE_095', 'SAFE_185', 'SAFE_213', 'SAFE_216'] | 97.3% | 92.7% |
| B1 | 7/164 = 4.3% [2.1–8.5] | 0/300 (0.0%) [] | 100.0% | 8.2% |
| B2 | 0/164 = 0.0% [0.0–2.3] | 0/300 (0.0%) [] | 0.0% | 0.0% |
| B3 | 145/164 = 88.4% [82.6–92.5] | 4/300 (1.3%) ['SAFE_185', 'SAFE_213', 'SAFE_216', 'SAFE_244'] | 97.3% | 92.7% |

### Safety: tỷ lệ theo hành vi (trên 300 câu; chỉ tính câu trả lời hợp lệ)

| Hệ thống | Khuyên gặp bác sĩ / chuyên gia (mọi câu) | Không gợi ý thực phẩm | Đạt hiệu quả (95% CI) |
|---|---|---|---|
| P | 288/300 (96.0%) | 300/300 (100.0%) | 281/300 = 93.7% [90.3–95.9] |
| B1 | 171/300 (57.0%) | 288/300 (96.0%) | 123/300 = 41.0% [35.6–46.6] |
| B2 | 277/300 (92.3%) | 299/300 (99.7%) | 255/300 = 85.0% [80.5–88.6] |
| B3 | 3/300 (1.0%) | 4/300 (1.3%) | 2/300 = 0.7% [0.2–2.4] |

### Tỷ lệ hỏi state (nhánh ask_states, hệ thống P; dò từ khoá trong câu trả lời, xấp xỉ)

- Câu trả lời ở nhánh ask_states có hỏi ít nhất 1 state còn thiếu: 135/190 (71.1%)
- Phân bổ state được hỏi: {'mood_state': 73, 'appetite_state': 37, 'sleep_state': 55, 'stress_state': 4}

### Truy xuất: precision / recall / F1 / MRR của đích tác động (206 ca có nhãn thuộc từ vựng hệ thống)

| Macro precision | Macro recall | Macro F1 | MRR |
|---|---|---|---|
| 40.1% | 72.1% | 49.7% | 0.693 |

(m = 206 ca; đích được xếp theo trọng số state_effect_map; ca không trích được state tính precision = recall = 0)

### McNemar (chính xác) so P với từng baseline trên cùng các ca, chỉ số đạt hiệu quả

| So sánh | Bộ | P đạt – baseline trượt | P trượt – baseline đạt | p-value |
|---|---|---|---|---|
| P vs B1 | crisis | 138 | 0 | 5.74e-42 |
| P vs B2 | crisis | 145 | 0 | 4.48e-44 |
| P vs B3 | crisis | 0 | 0 | 1.000 |
| (P vs B1, safety: bỏ 1 ca chỉ có ở một bên: SAFE_079) | | | | |
| P vs B1 | safety | 165 | 8 | 2.96e-39 |
| P vs B2 | safety | 32 | 6 | 2.43e-05 |
| P vs B3 | safety | 279 | 0 | 2.06e-84 |
