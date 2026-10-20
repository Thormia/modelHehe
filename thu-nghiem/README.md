# Các thử nghiệm (không thuộc hệ thống chính thức)

Hệ thống, kết quả và báo cáo **chính thức** là bản đánh giá ngày 16–17/10/2026 (code ở `Hybrid-database-main/`, kết quả ở
`eval_result_afterChangePrompt/`, báo cáo `BAO_CAO_KET_QUA_CUOI.docx`). Mọi thứ trong thư mục này là thử nghiệm làm sau
đợt đánh giá đó, **không** được dùng cho số liệu chính thức. Mỗi thử nghiệm được sửa sau khi đã xem kết quả trên bộ test,
nên nếu chạy lại trên cùng bộ test thì kết quả có thể thiên lệch; muốn dùng phải kiểm tra trên một bộ test mới.

Các file code trong từng thư mục giữ đúng đường dẫn tương đối như trong `Hybrid-database-main/`; muốn chạy thì chép đè
vào một bản sao của repo (không chép đè bản chính thức).

## 1_llm3-kiem-tra-khung-hoang (18/10)

Git worktree của nhánh `thu-nghiem/llm3-kiem-tra` (chuyển từ `thu-nghiem-llm3/`). Thêm một lượt gọi giám khảo `gemma3:4b`
sau LLM #1 để bắt khủng hoảng LLM #1 bỏ sót. Kết quả: crisis đạt hiệu quả 149 → 161/164, nhưng 157/958 hội thoại bình
thường bị chuyển sang phản hồi khủng hoảng. Chưa đưa vào hệ thống vì báo nhầm quá cao (báo cáo chính thức, mục hướng phát triển).

## 2_llm1-moi-llm3-p0-tpu-gpu (19–20/10)

Lấy từ `git stash` (`stash@{0}`, vẫn còn trong repo).
- LLM #1 gộp tự sát, tự hại, hoảng loạn cấp thành một cờ khủng hoảng; định nghĩa cờ y tế B3 mới.
- LLM #3 (`gemma3:12b`) kiểm tra câu trả lời cuối, thay guardrail tầng 2.
- P0 = hệ thống chính thức làm baseline; notebook chạy trên Kaggle TPU (vLLM) và GPU (Ollama).
- `expert_review/blind_eval/make_blind_form.py`: Google Form đánh giá mù P0, P, B1, B2, B3.
- `kaggle_upload/`: các gói đã gửi chạy và notebook lỗi `loi-eval-final-gpu-kaggle.ipynb` (có kết quả sơ bộ).

Kết quả sơ bộ trên GPU (chưa phân tích xong do thiếu 4 ca B2): so với P0, crisis 148 vs 149/164 (p = 1,0), safety
276 vs 285/300 (P0 tốt hơn, McNemar p = 0,049); LLM #1 mới phát hiện khủng hoảng 141/164 (bản chính thức 148). Không dùng.

## 3_prompt-b3 (20/10)

Chỉ sửa định nghĩa cờ y tế B3 trong prompt LLM #1 (`Hybrid-database-main/backend/extractor.py`): rượu bia, thuốc lá/vape,
cà phê, nhịn ăn, thức trắng chỉ là B3 khi đã gây triệu chứng thể chất. Tập dev 16 câu tự viết
(`Hybrid-database-main/scripts/dev_b3_check.py`): 11/16 → 15/16.

Chạy lại trên Kaggle GPU ngày 20/10, cùng hạ tầng, model và bộ test với bản chính thức (`eval_result_promptB3/`;
bảng số `eval_result_promptB3/analyze_final_output.md`). So với bản chính thức trên cùng các ca:

| Chỉ số (P) | Chính thức 16/10 | Prompt B3 20/10 | So cặp |
|---|---|---|---|
| Khủng hoảng đạt hiệu quả | 149/164 | 145/164 | 0 tốt lên, 4 xấu đi; p = 0,125 |
| An toàn đạt hiệu quả | 278/300 | 281/300 | 12 tốt lên, 9 xấu đi; p = 0,66 |
| Truy xuất theo 4 state (đúng chiều) | 269/295 | 271/295 | |
| Cờ y tế B3 (tình trạng thuộc định nghĩa) | 169/224 | 171/224 | |

Cờ y tế: tốt lên ở rượu bia (5 → 13/21), nhịn ăn có triệu chứng (6 → 12/13), thức trắng có triệu chứng (0 → 5/10),
cà phê (2 → 4/9); xấu đi ở kỳ kinh (15 → 7/19), mang thai (21 → 16/21), cai thuốc lá/vape (6 → 2/16), vừa mổ (19 → 18);
bật nhầm 3 ca không kể triệu chứng (bản chính thức 0). Không có thay đổi nào có ý nghĩa thống kê. B1 safety thiếu 1 ca
(SAFE_079, server trả lỗi 500).

`kaggle_upload/`: gói `huhu-system-final-prompt-b3.zip` và thư mục đã gửi chạy.
