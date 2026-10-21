# Chatbot tâm lý – dinh dưỡng cho người Việt (multi-agent, Stateful Hybrid RAG)

*A Multi-Agent Chatbot with Stateful Hybrid RAG for Mental Health Support among Vietnamese Users through Nutritional Therapy*

Chatbot trò chuyện thấu cảm và, khi đủ thông tin về 4 trạng thái của người dùng (giấc ngủ, ăn uống, căng thẳng, tâm trạng),
gợi ý thực phẩm Việt Nam có căn cứ, không định lượng, không chẩn đoán. Luồng mỗi lượt:

```
Tin nhắn ─► LLM #1 (Qwen2.5-7B-Instruct): 4 states, cờ y tế (B3), cờ khủng hoảng ─► định tuyến
   ├─ khủng hoảng / hoảng loạn ─► phản hồi soạn sẵn (115, đường dây nóng)
   ├─ cờ y tế ──────────────────► khuyên hỏi bác sĩ, không gợi ý món
   ├─ chưa đủ 4 states ─────────► hỏi thêm
   └─ đủ 4 states ──────────────► truy xuất PostgreSQL (state_effect_map, pgvector CBT)
LLM #2 (qwen-huhu = Qwen2.5-7B-Instruct + LoRA fine-tune) ─► Guardrail tầng 1 (luật) ─► tầng 2 (gemma3:4b) ─► người dùng
```

## Bản chính thức

Nhánh `main` là bản chính thức: hệ thống đã đánh giá trên Kaggle (lần chạy cuối 20/10/2026, cùng hệ thống với lần chạy
16–17/10), kết quả và báo cáo tương ứng. Số liệu báo cáo lấy từ lần chạy cuối.

| Muốn xem | Ở đâu |
|---|---|
| Báo cáo kết quả cuối (Word, có biểu đồ) | `BAO_CAO_KET_QUA_CUOI.docx` |
| Báo cáo đánh giá đầy đủ (Markdown) | `Hybrid-database-main/logs/eval/BAO_CAO_DANH_GIA.md` |
| Kết quả đánh giá gốc (từng ca) | `eval_result_final/` (lần chạy cuối 20/10) |
| Ý tưởng, thiết kế, quy ước dữ liệu, việc còn mở | `idea.docx` |
| Code hệ thống, cách cài và chạy | `Hybrid-database-main/` (xem `Hybrid-database-main/README.md`) |
| Các thử nghiệm sau đánh giá (không dùng cho số chính thức) | `thu-nghiem/` (xem `thu-nghiem/README.md`) |

## Model fine-tune (Kaggle)

| Bước | Notebook trong repo | Bản đã chạy trên Kaggle |
|---|---|---|
| Fine-tune Qwen2.5-7B-Instruct bằng LoRA trên TPU (ra `best_adapter`) | `finetune_modelhuhu.ipynb` | https://www.kaggle.com/code/ghoenix/modelhuhu/log |
| Đánh giá model fine-tune so với model gốc trên tập test fine-tune (perplexity, ROUGE-L, BERTScore, định dạng JSON) | `huhuevalu.ipynb` | https://www.kaggle.com/code/ghoenix/huhuevalu |
| Gộp LoRA, xuất GGUF Q4_K_M để chạy bằng Ollama (ra `qwen2.5-7b-huhu-Q4_K_M.gguf`) | `uploadhuhu.ipynb` (= `Hybrid-database-main/serving/export_gguf_kaggle.ipynb`) | https://www.kaggle.com/code/ghoenix/uploadhuhu |

- Log huấn luyện: `Hybrid-database-main/logs/finetune/run_log.txt`, `train_history.json` (loss theo bước, dùng vẽ biểu đồ trong báo cáo).
- `generations.jsonl`: câu trả lời sinh ra trong `huhuevalu.ipynb` (model fine-tune và model gốc), dùng tính ROUGE-L, BERTScore.
- Trọng số không nằm trong repo (vượt giới hạn GitHub): `best_adapter` ở Output của notebook fine-tune; file GGUF
  (sha256 `91bfc32083ce6f7f67811561c461c0308ab32222655bd433473b60b6f3bacb8d`) ở Output của notebook upload.

## Cấu trúc thư mục

### Hệ thống (`Hybrid-database-main/`)

| Thư mục / file | Nội dung, dùng để làm gì |
|---|---|
| `backend/` | Chatbot: `pipeline.py` (luồng mỗi lượt), `extractor.py` (LLM #1), `prompting.py` (system prompt giống từng ký tự dữ liệu train), `guardrails.py`, `safety.py` (từ khoá, phản hồi khủng hoảng), `session.py` (Redis), `api.py` + `static/` (giao diện chat) |
| `retrieval/` | `state_retriever.py`: 4 states → đích tác động (`state_effect_map`) → món ăn; `hybrid_retriever.py`: truy xuất Graph RAG + vector |
| `db/`, `ingestion/` | Lược đồ PostgreSQL/pgvector, Neo4j; `seed_all.py` nạp toàn bộ dữ liệu |
| `data/processed/` | Dữ liệu hệ thống dùng khi chạy: 400 món ăn, `state_effect_map.json` (ontology theo Xhani et al., 2026), danh mục CBT, kho tâm lý |
| `serving/` | `Modelfile` (Ollama), `export_gguf_kaggle.ipynb`, `eval_final_kaggle.ipynb` và `eval_grounding_kaggle.ipynb` (chạy đánh giá trên Kaggle GPU), `kaggle_services.sh` (dựng PostgreSQL, Redis, Neo4j, Ollama trên Kaggle) |
| `scripts/` | Đánh giá và báo cáo (bảng dưới) |
| `tests/` | Unit test (không cần model hay database) |
| `logs/eval/` | `BAO_CAO_DANH_GIA.md`; `chamtay_after_b3fix.md` (chấm tay các ca trượt, chỉ để phân tích lỗi) |

| Script (`Hybrid-database-main/scripts/`) | Dùng để |
|---|---|
| `eval_system.py` | Chạy bộ test: `crisis` (LLM #1 phát hiện khủng hoảng), `retrieval` (truy xuất theo 4 state), `safety` |
| `eval_baselines.py` | Sinh câu trả lời và chấm hệ thống đề xuất (P) cùng 3 baseline (Baseline 1, 2, 3; mã `B1`, `B2`, `B3` trong code, khác với nhóm dữ liệu B1–B4) trên bộ crisis và safety |
| `eval_grounding.py` | Grounding nhánh dinh dưỡng và định tuyến qua nhiều lượt trên tập test fine-tune |
| `eval_rules.py` | Quy tắc chấm dùng chung (truy xuất theo 4 state, nhóm cờ y tế B3) cho script đánh giá và báo cáo |
| `analyze_final.py` | Phân tích chi tiết từ kết quả đã có: đạt hiệu quả, phản hồi khẩn cấp, McNemar… (không chạy lại model) |
| `build_final_report.py`, `report_charts.py` | Dựng `BAO_CAO_KET_QUA_CUOI.docx` và biểu đồ từ file kết quả |
| `expert_agreement.py` | Tổng hợp phiếu chuyên gia, tính Fleiss' κ, Krippendorff's α, Gwet's AC |
| `judge_bench.py` | Chọn model giám khảo trên 32 ca tự soạn |
| `make_kaggle_package.py` | Đóng gói hệ thống kèm sha256 từng file để chạy đánh giá trên Kaggle |
| `make_flowcharts.py`, `chat_cli.py` | Vẽ sơ đồ hệ thống; chat thử trên terminal |

### Dữ liệu

| Thư mục / file | Nội dung |
|---|---|
| `data/300 test/` | 3 bộ test, mỗi bộ 300 câu (tiếng Việt và tiếng Anh): khủng hoảng, truy xuất, ranh giới an toàn |
| `data/data-finetune/` | Hội thoại tư vấn tâm lý dịch sang tiếng Việt (nguồn nhóm A): `output_vi.jsonl` (bản dịch), `finetune.jsonl`, `finalfinetune.jsonl`; `MASTER_PROMPT_DICH.txt`, `RUNBOOK.txt`, `tool.py` (quy trình và công cụ dịch) |
| `data/data-generative/` | QA tự sinh: context RAG → câu trả lời chuyển từ đồng cảm sang gợi ý dinh dưỡng (`generative.jsonl`), prompt sinh và script sửa |
| `data/Data-RAG/` | Kho RAG gốc: 400 món ăn (`400 data dinh duong_v3.json`), kho tâm lý (vi, en), prompt sinh dữ liệu dinh dưỡng, `ref_data.txt` (nguồn tham khảo), `vn_food_table.pdf` (bảng thành phần thực phẩm Việt Nam) |
| `data/group_A*.jsonl`, `data/group_B*.jsonl` | Dữ liệu nhóm A (trò chuyện thấu cảm) và nhóm B (theo nhánh B1–B4) trước khi định dạng; `*_flagged`, `group_B_check` là kết quả rà soát |
| `traindata/` | Dữ liệu train/test đúng định dạng fine-tune: nhóm A, B1 (hỏi thêm state), B2 (gợi ý món), B3 (cờ y tế), B4; `test_*` là tập test fine-tune (dùng cho `huhuevalu.ipynb` và đánh giá grounding); `safetyguard.jsonl` là các mẫu khủng hoảng / dùng thuốc được tách riêng |
| `traindata_logs/` | Script và nhật ký làm sạch dữ liệu train: kiểm định dạng, sửa, bỏ trùng, đo gần trùng nhóm A; `change_log.jsonl`, `removed_samples.jsonl` |

### Đánh giá

| Thư mục / file | Nội dung |
|---|---|
| `eval_result_final/eval_final_results/` | Kết quả chính thức (lần chạy cuối 20/10): crisis, retrieval, P và 3 baseline (câu trả lời và điểm từng ca; tên file `B1/B2/B3_*` = Baseline 1/2/3), `turns.jsonl` (trace từng lượt của pipeline), `analysis_final.json`, `logs/eval/run_*.txt` (các bảng notebook in ra) |
| `eval_result_final/eval_grounding_results/` | Kết quả chính thức (20/10): grounding mức model và toàn hệ thống, định tuyến nhiều lượt |
| `eval_result_afterChangePrompt/` | Lần chạy 16–17/10 (cùng hệ thống); chấm tay phân tích lỗi làm trên lần chạy này |
| `expert_review/` | Lấy mẫu dữ liệu gửi chuyên gia (`sample_for_experts.py`, `samples.json`) |
| `expert_feedback/` | Phiếu chấm chuyên gia đã ẩn danh (`anonymized/`, 8 người chấm), `agreement.json` (độ đồng thuận), `TONG_KET_CHUYEN_GIA.md` (tổng kết và nhận xét) |
| `flowchart_he_thong.drawio`, `flowchart_du_lieu.drawio` | Sơ đồ luồng hệ thống và quy trình dữ liệu (mở bằng draw.io) |

### Thử nghiệm (`thu-nghiem/`)

Các thử nghiệm làm sau đợt đánh giá chính thức (lớp kiểm tra khủng hoảng thứ hai; LLM #1 mới + LLM #3 trên TPU/GPU; sửa
định nghĩa cờ y tế B3), kèm kết quả và lý do không đưa vào hệ thống. Chi tiết: `thu-nghiem/README.md`.

## Tái lập

1. Cài và chạy hệ thống: `Hybrid-database-main/README.md` (Docker cho PostgreSQL/Neo4j/Redis, Ollama với 3 model, `seed_all.py`).
2. Chạy lại đánh giá: `python scripts/make_kaggle_package.py` rồi chạy 2 notebook `serving/eval_*_kaggle.ipynb` trên Kaggle
   GPU T4 x2; notebook kiểm sha256 từng file và digest model trước khi chạy. Các cell in trực tiếp các bảng của báo cáo.
3. Dựng lại báo cáo từ kết quả có sẵn: `python scripts/analyze_final.py <thư mục kết quả>` rồi `python scripts/build_final_report.py`.

## Lưu ý khi đọc kết quả

- Mọi số chấm câu trả lời là số chấm tự động, cùng giám khảo (gemma3:4b) và cùng code cho hệ thống đề xuất và 3 baseline;
  chấm tay chỉ có cho hệ thống đề xuất nên chỉ dùng để phân tích lỗi.
- Một số cách chấm được nhóm chốt sau khi đã có kết quả 16–17/10: truy xuất chấm theo 4 state (không tính câu chỉ có
  nhãn digestion/impulsivity_control), định tuyến chỉ chấm khi thông tin đã có trong hội thoại, nhịn ăn/thức trắng chỉ
  tính là cờ y tế khi có triệu chứng thể chất. Lý do ghi trong báo cáo.
- Không có trong repo: trọng số model, `.env` (mẫu ở `Hybrid-database-main/.env.example`), phiếu chuyên gia bản gốc có
  họ tên, các gói zip đóng gói cho Kaggle.
