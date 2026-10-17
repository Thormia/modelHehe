# HYBRID DATABASE PIPELINE (GRAPH RAG + VECTOR / SQL)
### Đề tài: Chatbot hỗ trợ sức khỏe tinh thần cho người Việt Nam bằng thực dưỡng

Hệ thống Hybrid Database kết hợp đa mô hình lưu trữ: **PostgreSQL + pgvector** (Dữ liệu quan hệ & Vector Search ngữ nghĩa), **Neo4j** (Đồ thị tri thức Trục Não - Ruột / Triệu chứng - Vi chất - Thực phẩm), và **Redis** (Bộ nhớ đệm / Cache / Quản lý phiên hội thoại).

---

## 1. CẤU TRÚC THƯ MỤC HỆ THỐNG

```
Code/
├── docker-compose.yml              # Khởi chạy cụm CSDL: PostgreSQL 16 (pgvector), Neo4j 5.18, Redis
├── requirements.txt                # Danh sách thư viện Python cần thiết
├── .env.example                    # File cấu hình biến môi trường mẫu
├── .env                            # File biến môi trường đang hoạt động
├── verify_hybrid_rag.py            # Script kiểm thử toàn diện luồng Hybrid RAG
├── visualize_graph.py              # Script xuất biểu đồ mạng đồ thị tương tác HTML (PyVis)
│
├── data/
│   └── processed/                  # Dữ liệu chuẩn định dạng JSON
│       ├── 400 data dinh duong.json       # 400 món ăn Việt Nam & vi chất (100% không định lượng số học)
│       └── psychology_dataset_vi.json     # 988 mẫu bệnh cảnh tâm lý & cơ chế sinh hóa trục Não - Ruột
│
├── db/                             # Lược đồ và Quản lý kết nối
│   ├── schema.sql                  # Lược đồ bảng SQL & pgvector cho PostgreSQL
│   ├── graph_schema.cypher         # Ràng buộc & Chỉ mục cho Neo4j Graph Database
│   └── db_clients.py               # Module quản lý kết nối CSDL tập trung
│
├── ingestion/                      # Bộ công cụ nạp dữ liệu (ETL / Seeding)
│   ├── ingest_postgres.py          # Nạp dữ liệu SQL quan hệ + trích xuất Vector nhúng
│   ├── ingest_neo4j.py             # Xây dựng Đồ thị tri thức đa chiều (Symptom -> Nutrient -> Food)
│   └── seed_all.py                 # Pipeline nạp đồng bộ toàn bộ CSDL chỉ bằng 1 lệnh
│
├── retrieval/                      # Module Truy xuất thông minh
│   ├── hybrid_retriever.py         # Bộ máy kết hợp Graph RAG + Vector Search + Lọc thuộc tính SQL
│   └── state_retriever.py          # Truy xuất theo 4 states cho chatbot, xuất đúng định dạng dữ liệu fine-tune
│
├── backend/                        # Chatbot hoàn chỉnh (mục 6)
│   ├── pipeline.py                 # Luồng mỗi lượt: LLM #1 + keyword -> định tuyến -> LLM #2 -> Guardrail
│   ├── extractor.py                # LLM #1: trích 4 states, cờ thuốc, cờ khủng hoảng
│   ├── safety.py                   # Bộ từ khóa an toàn + phản hồi khủng hoảng soạn sẵn
│   ├── prompting.py                # Dựng system prompt đúng từng ký tự như dữ liệu train
│   ├── guardrails.py               # Guardrail tầng 1 (luật) + tầng 2 (LLM giám khảo)
│   ├── session.py                  # Phiên hội thoại trên Redis
│   ├── api.py, static/index.html   # API FastAPI + giao diện chat thử
│   └── constants.py, config.py, llm.py
├── serving/                        # Đưa model fine-tune lên Ollama
│   ├── export_gguf_kaggle.ipynb    # Gộp LoRA + xuất GGUF Q4_K_M (chạy trên Kaggle CPU)
│   └── Modelfile
├── scripts/chat_cli.py             # Chat thử trên terminal
└── tests/test_backend.py           # Test với LLM / DB giả lập
```

---

## 2. NGUYÊN TẮC DỮ LIỆU & RÀNG BUỘC MIỀN (DOMAIN CONSTRAINTS)

Toàn bộ hệ thống tuân thủ nghiêm ngặt 2 tiêu chuẩn y khoa - thực dưỡng:
1. **Tuyệt đối không định lượng số học:** Loại bỏ hoàn toàn các con số cụ thể (`mg`, `g`, `kcal`, `ml`, `mcg`) trong khuyến nghị dinh dưỡng để tránh rủi ro y tế và quá liều vi chất.
2. **Tuyệt đối không bài tập tâm lý học lâm sàng:** Không đưa bài tập thở, viết nhật ký, thiền sâu, CBT (Liệu pháp nhận thức - hành vi) vào dữ liệu dinh dưỡng; chỉ tập trung vào cơ chế sinh hóa thực dưỡng của **Trục Não - Ruột (Gut-Brain Axis)**.

---

## 3. CÁC TẬP DỮ LIỆU CHÍNH (`data/processed/`)

| Tên File | Số lượng bản ghi | Mục đích sử dụng trong Hybrid Pipeline |
| :--- | :--- | :--- |
| `400 data dinh duong.json` | 400 món ăn | Nạp vào PostgreSQL (lưu chi tiết món ăn, phân nhóm, cách chế biến) và Neo4j (tạo node `Food`, nối quan hệ `CONTAINS_NUTRIENT` tới `Nutrient`). |
| `psychology_dataset_vi.json` | 988 ca tâm lý | Nạp vào Neo4j (tạo node `Symptom`, `Mechanism`, `Nutrient` và các quan hệ 2 chiều) & PostgreSQL (lưu ca bệnh để tìm kiếm ngữ nghĩa vector). |

---

## 4. QUY TRÌNH CHẠY HỆ THỐNG THỦ CÔNG CHI TIẾT

### Bước 1: Chuẩn bị môi trường & CSDL
1. Tạo môi trường ảo Python và cài đặt thư viện:
   ```bash
   python -m venv venv
   # Trên Windows:
   .\venv\Scripts\activate
   # Cài đặt thư viện:
   pip install -r requirements.txt
   ```
2. Khởi động các container CSDL (PostgreSQL, Neo4j, Redis):
   ```bash
   docker-compose up -d
   ```
3. Kiểm tra các dịch vụ đang chạy:
   - **PostgreSQL**: `localhost:5432` (User: `postgres`, Pass: `postgres123`, DB: `mental_health_nutrition`)
   - **Neo4j Browser**: `http://localhost:7474` (User: `neo4j`, Pass: `password123`, theo `docker-compose.yml`)
   - **Redis**: `localhost:6379`

---

### Bước 2: Nạp dữ liệu vào Hybrid Database (Seeding)

Chạy 1 lệnh duy nhất để tự động khởi tạo bảng, ràng buộc và nạp toàn bộ dữ liệu vào PostgreSQL & Neo4j:
```bash
python ingestion/seed_all.py
```

*Hoặc có thể chạy riêng lẻ từng cơ sở dữ liệu nếu cần debug:*
- Chỉ nạp PostgreSQL: `python ingestion/ingest_postgres.py`
- Chỉ nạp Neo4j: `python ingestion/ingest_neo4j.py`

---

### Bước 3: Kiểm thử Truy xuất Kết hợp (Hybrid Retrieval Verification)

Chạy script kiểm thử để thực hiện truy vấn mẫu qua cả 2 kênh (Graph RAG + Vector/SQL):
```bash
python verify_hybrid_rag.py
```
Script sẽ thực hiện:
- Mô phỏng truy vấn người dùng: *"Tôi bị stress và mất ngủ kéo dài, nên ăn gì?"*
- **Graph RAG (Neo4j)**: Truy vết `Stress / Mất ngủ` $\rightarrow$ `Thiếu hụt Magie / Tryptophan / GABA` $\rightarrow$ `Món ăn giàu vi chất tương ứng`.
- **Vector Search (PostgreSQL)**: So khớp ngữ nghĩa không gian vector của triệu chứng.
- **SQL Filter**: Lọc theo điều kiện đối tượng (ví dụ: ăn chay, không dị ứng).

---

### Bước 4: Trực quan hóa Đồ thị Tri thức (Interactive Graph Visualizer)

Để xem trực tiếp đồ thị mạng lưới liên kết đa chiều giữa **Triệu chứng $\leftrightarrow$ Vi chất $\leftrightarrow$ Món ăn**:
```bash
python visualize_graph.py
```
File giao diện tương tác `visualize_graph.html` sẽ được tạo ra. Bạn chỉ cần mở file này bằng trình duyệt bất kỳ (Chrome, Edge, Firefox) để:
- Zoom, kéo thả các cụm thực phẩm và triệu chứng.
- Xem liên kết 2 chiều giữa nhiều món ăn có chung vi chất và cơ chế sinh hóa.

---

## 5. KIẾN TRÚC TRUY XUẤT HYBRID DATABASE

```
                  ┌────────────────────────────────────────┐
                  │          User Query (Tiếng Việt)       │
                  └───────────────────┬────────────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
                 ▼                                         ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │    Neo4j (Graph RAG)      │             │  PostgreSQL (pgvector)    │
   │  Traverse 2 chiều:        │             │  Semantic Vector Search   │
   │  Symptom -> Nutrient      │             │  + SQL Attribute Filter   │
   │  -> Mechanism -> Food     │             │  (Category, Cooking, etc.)│
   └─────────────┬─────────────┘             └─────────────┬─────────────┘
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Hybrid RAG Retriever    │
                        │   (Deduplicate & Rerank)  │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │  Context hoàn chỉnh cho   │
                        │  LLM sinh lời khuyên      │
                        └───────────────────────────┘
```

---

## 6. CHATBOT HOÀN CHỈNH (BACKEND + MODEL FINE-TUNE)

Hiện thực luồng trong `idea.docx`:

```
Tin nhắn ─┬─ LLM #1 (qwen2.5:7b-instruct): 4 states, medication_alert, crisis_flag
          └─ Bộ từ khóa an toàn                                   (chạy song song)
   │
   ├─ Có cờ khủng hoảng ──────────────► Phản hồi soạn sẵn (không gọi LLM #2)
   ├─ Có cờ thuốc (giữ cả phiên) ─────► medication : ROUTE false + SYSTEM_OVERRIDE      (B3)
   ├─ Chưa đủ 4 states ───────────────► ask_states : ROUTE false + MISSING_STATES       (B1, B4)
   ├─ Đủ states, đã gợi ý, không đổi ─► side_talk  : ROUTE false                        (A)
   └─ Đủ 4 states ────────────────────► nutrition  : SQL state_effect_map + pgvector CBT, ROUTE true (B2)
   │
   ▼
LLM #2 (model fine-tune qwen-huhu) ─► Guardrail tầng 1 (luật) ─► Guardrail tầng 2 (LLM giám khảo)
   (lỗi: sinh lại tối đa 2 lần, rồi sửa tối thiểu / câu trả lời dự phòng)   ─► Người dùng
```

Prompt gửi cho LLM #2 được dựng **giống từng ký tự** với dữ liệu fine-tune
(test `test_rebuild_every_training_system_prompt` dựng lại toàn bộ system prompt trong `traindata/` và so khớp).
Dòng context có dạng `NUT_306 – Hải sâm | Tryptophan | REGULATING | điều hòa dẫn truyền thần kinh`
(mã `NUT_xxx` = thứ tự 1-based trong `400 data dinh duong.json`) và
`PSY_MINDFUL_0001 – Nhận thức hơi thở (Breath Awareness) | ...` (danh mục `cbt_catalog.json`).

### Bước 1: Database
```bash
docker-compose up -d
pip install -r requirements.txt
python ingestion/seed_all.py      # BẮT BUỘC chạy lại: thêm cột nut_code, bảng state_effect_map, cbt_catalog
```

### Bước 2: Đưa model fine-tune lên Ollama
1. Trên Kaggle: mở `serving/export_gguf_kaggle.ipynb`, Accelerator = None, Add Input dataset chứa `best_adapter`,
   *Save & Run All*. Tải `qwen2.5-7b-huhu-Q4_K_M.gguf` (~4.7 GB) ở tab Output về thư mục `serving/`.
2. Trên máy:
   ```bash
   cd serving
   ollama create qwen-huhu -f Modelfile
   ollama pull qwen2.5:7b-instruct     # LLM #1
   ollama pull gemma3:4b               # giám khảo Guardrail tầng 2 và giám khảo eval (Google, khác gốc Qwen để chấm chéo)
   ```
   Có GPU lớn thì có thể dùng vLLM thay Ollama (không cần gộp/lượng tử hóa):
   `vllm serve Qwen/Qwen2.5-7B-Instruct --enable-lora --lora-modules qwen-huhu=/đường/dẫn/best_adapter --max-lora-rank 16`,
   rồi đặt `GEN_BASE_URL=EXT_BASE_URL=JUDGE_BASE_URL=http://localhost:8000/v1`, `EXT_MODEL=Qwen/Qwen2.5-7B-Instruct`, `JUDGE_MODEL=google/gemma-3-4b-it`.

### Bước 3: Chạy chatbot
```bash
copy .env.example .env               # Windows (Linux/macOS: cp)
uvicorn backend.api:app --port 8000  # giao diện chat: http://localhost:8000  (tick "chi tiết" để xem nhánh, states)
# hoặc chat trên terminal:
python scripts/chat_cli.py
```
API: `POST /chat {"message": "...", "session_id": null}` → `{reply, branch, states, medication, output, session_id}`;
`GET/DELETE /session/{id}`; `GET /health`.

Mỗi lượt được ghi vào `logs/turns.jsonl` (states, cờ, system prompt, output thô, lỗi Guardrail từng lần thử)
để phục vụ đánh giá toàn hệ thống.

### Bước 4: Test
```bash
python -m unittest discover -s tests -v          # unit test, không cần Ollama / Docker

# Test toàn hệ thống trên data/300 test (kết quả từng ca: logs/eval/*.jsonl)
python scripts/eval_system.py crisis              # 164 ca thuộc định nghĩa khủng hoảng: tỷ lệ LLM #1 phát hiện
python scripts/eval_system.py retrieval           # 300 ca: states -> đích tác động so với expected_effects (cần LLM #1)
python scripts/eval_system.py safety              # 300 bẫy liều lượng / chẩn đoán / thuốc / calo (cần cả hệ thống)
python scripts/eval_system.py safety --limit 20   # chạy thử ít ca trước

# So sánh với 3 baseline (P = hệ thống đề xuất; B1 = Qwen2.5-7B gốc trả lời trực tiếp; B2 = qwen-huhu trả lời trực tiếp;
# B3 = pipeline + Qwen2.5-7B gốc) trên crisis (164 ca) và safety (300 ca)
python scripts/eval_baselines.py gen   --systems P B1 B2 B3 --suites crisis safety   # pha 1: sinh câu trả lời
python scripts/eval_baselines.py score --systems P B1 B2 B3 --suites crisis safety   # pha 2: chấm (JUDGE_MODEL)
python scripts/eval_baselines.py report
```

**Chạy bản final trên Kaggle** (GPU T4 x2, Internet On; cả 3 model nằm cùng lúc trên GPU nên nhanh hơn máy 6 GB):
1. `python scripts/make_kaggle_package.py` tạo `../kaggle_upload/huhu-system-final.zip` (code, data, bộ test, traindata và
   `manifest.json` ghi sha256 từng file, sha256 GGUF, digest model Ollama ở máy local, revision bge-m3).
2. Tạo dataset Kaggle từ file zip; GGUF dùng Output của `export_gguf_kaggle` hoặc dataset riêng.
3. Mở `serving/eval_final_kaggle.ipynb`, Add Input 2 thứ trên, *Run All*. Notebook kiểm sha256/digest (lệch là dừng),
   dựng PostgreSQL 16 + pgvector, Redis, Neo4j 5.18, Ollama bằng `serving/kaggle_services.sh` (thay docker-compose),
   seed DB, kiểm số dòng, so truy xuất PostgreSQL với bản JSON, chạy unit test, rồi chạy toàn bộ bộ test. Kết quả:
   `/kaggle/working/eval_final_results.zip`. Hết 12 giờ thì gắn Output làm input và chạy lại: ca đã xong được bỏ qua.
**Kết quả chính thức và cách dựng lại báo cáo** (lần chạy 16–17/10 sau khi sửa lỗi implement nhóm B3):
- Output 2 notebook Kaggle nằm ở `../eval_result_afterChangePrompt/` (`eval_final_results (1)/` cho crisis, retrieval, safety và 3 baseline;
  `eval_grounding_results/` cho grounding và định tuyến nhiều lượt). Báo cáo chỉ dùng số của lần chạy này.
- `python scripts/analyze_final.py "../eval_result_afterChangePrompt/eval_final_results (1)"` tính lại các chỉ số chi tiết
  (recall/F1, McNemar, theo loại bẫy…) mà không chạy lại model.
- `python scripts/build_final_report.py` sinh `../BAO_CAO_KET_QUA_CUOI.docx` từ các file kết quả trên; báo cáo đầy đủ ở
  `logs/eval/BAO_CAO_DANH_GIA.md`, chấm tay (chỉ để phân tích lỗi) ở `logs/eval/chamtay_after_b3fix.md`.
- Trọng số không nằm trong repo (vượt 100 MB): `best_adapter` là Output của notebook fine-tune `../finetune_modelhuhu.ipynb`,
  GGUF là Output của `serving/export_gguf_kaggle.ipynb`; sha256 GGUF ghi trong `manifest.json` của gói Kaggle.

Chưa bật Docker vẫn chạy được toàn hệ thống với `RETRIEVER=offline` trong `.env` (đọc thẳng file JSON, cùng logic chọn món,
không có `CBT_CONTEXT`); phiên hội thoại tự lưu trong bộ nhớ nếu không có Redis.

Khủng hoảng theo định nghĩa của nhóm gồm tự sát, tự hại và hoảng loạn cấp đang diễn ra (do LLM #1 quyết định qua
crisis_flag / panic_flag; từ khóa chỉ dự phòng khi LLM #1 lỗi); script crisis chỉ chấm các loại này.

### Lưu ý và việc còn mở
- **`state_effect_map.json`** dựng theo ontology của Xhani et al. (2026), *Modelling Food and Mood Relation with Dynamic
  Personas* (MODELSWARD 2026); mỗi dòng có trường `source` ghi mục/hình trong bài. Bảng 400 thực phẩm (bản cuối) chỉ có
  các đích stress_response, mood_regulation, neurotransmission, digestion, nên giấc ngủ và ăn uống được nối qua cơ chế
  nền Neurotransmission (mục 3.3) và Digestion (Figure 3). Sửa JSON rồi chạy lại `seed_all.py`.
- **Nhãn states**: `mood_state` theo state chart của bài báo (Calm, Stressed, LowMood, Recovering, Energized);
  nhãn của `sleep_state`, `appetite_state`, `stress_state` (`backend/constants.py`) bài báo không định nghĩa, vẫn cần nhóm chốt.
- `NUT_060` (nhút) đang bị loại khỏi gợi ý cho tới khi xác minh `ontology_effect` (idea.docx: Việc còn mở).
- `CRISIS_HOTLINE_TEXT` trong `.env`: đã điền Ngày Mai 096 306 1414 và 111 (trẻ em); 115 luôn có trong câu trả lời khủng hoảng. Nên gọi thử để xác nhận giờ trực của Ngày Mai.
- Bản Q4_K_M chạy trên Ollama có thể lệch nhẹ so với bản bf16 đã đánh giá trên Kaggle.
- GPU 6 GB chỉ giữ được 1 model 7–8B mỗi lúc: Ollama nạp luân phiên LLM #1, LLM #2 và giám khảo (3 model khác nhau)
  nên mỗi lượt mất khoảng 1–2 phút. Có thể dùng `EXT_MODEL=qwen2.5:3b-instruct` hoặc tắt tầng 2 khi demo
  (`GUARDRAIL_L2_ENABLED=false`).
- Giám khảo (tầng 2 và chấm eval) chọn trên 32 ca tự soạn (`scripts/judge_bench.py`), theo hành động cuối (sinh lại /
  bỏ gợi ý món): gemma3:4b 30/32, aya-expanse:8b 27/32, qwen2.5:7b 26/32. Chọn gemma3:4b: khác gốc với model fine-tune
  (Qwen) và đúng nhiều nhất. Bench nhỏ, số dao động giữa các lần chạy.
- Luồng chat dùng PostgreSQL (SQL + pgvector) và Redis; Neo4j vẫn dùng cho `hybrid_retriever.py` và trực quan hóa đồ thị.
