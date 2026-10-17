"""Sinh 2 flowchart dạng draw.io (mxGraph XML): luồng hệ thống và luồng dữ liệu.

    python scripts/make_flowcharts.py      ->  ../flowchart_he_thong.drawio, ../flowchart_du_lieu.drawio

Mở bằng draw.io (app.diagrams.net): File > Open from > Device, hoặc Extras > Edit Diagram để dán XML.
Nội dung bám theo backend/pipeline.py, retrieval/state_retriever.py, backend/guardrails.py, ingestion/ và idea.docx.
"""
import os
import sys
from xml.sax.saxutils import escape

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
AIM = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

S = {
    "term": "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1;",
    "proc": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;arcSize=8;",
    "llm": "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;arcSize=8;",
    "dec": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
    "safe": "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;arcSize=8;",
    "branch": "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;arcSize=8;",
    "db": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;fillColor=#f5f5f5;strokeColor=#666666;",
    "data": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#f5f5f5;strokeColor=#666666;size=0.15;",
    "out": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;arcSize=8;",
    "lane": "swimlane;whiteSpace=wrap;html=1;startSize=30;fillColor=#f9f9f9;strokeColor=#999999;fontStyle=1;fontSize=14;",
    "note": "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=11;fontColor=#444444;",
    "title": "text;html=1;whiteSpace=wrap;align=center;fontSize=18;fontStyle=1;",
}
E = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;"
ED = E + "dashed=1;"


class Diagram:
    def __init__(self, name):
        self.name, self.cells, self.n = name, [], 2

    def node(self, label, x, y, w, h, kind, parent="1"):
        cid = f"n{self.n}"
        self.n += 1
        v = escape(label).replace("\n", "&lt;br&gt;")
        self.cells.append(f'<mxCell id="{cid}" value="{v}" style="{S[kind]}" vertex="1" parent="{parent}">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return cid

    def edge(self, a, b, label="", dashed=False, extra=""):
        cid = f"e{self.n}"
        self.n += 1
        self.cells.append(f'<mxCell id="{cid}" value="{escape(label)}" style="{(ED if dashed else E) + extra}" edge="1" parent="1" '
                          f'source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')

    def xml(self):
        return ('<mxfile host="app.diagrams.net"><diagram name="' + escape(self.name) + '"><mxGraphModel dx="1400" dy="900" grid="1" '
                'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0">'
                '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(self.cells) + "</root></mxGraphModel></diagram></mxfile>")


# ====================================================================== HỆ THỐNG
def system():
    d = Diagram("Luồng hệ thống")
    d.node("Luồng xử lý một lượt chat của hệ thống (bản final)", 160, -70, 760, 40, "title")
    X, W = 380, 260  # cột chính
    L, R = 40, 760   # cột nhánh trái, cột phản hồi an toàn bên phải
    u = d.node("Người dùng nhắn tin", X + 30, 0, 200, 50, "term")
    api = d.node("FastAPI POST /chat\nNạp phiên từ Redis (TTL 24 giờ):\nlịch sử, states, cờ y tế, món đã gợi ý", X, 90, W, 70, "proc")
    ext = d.node("LLM #1 – Extractor\nqwen2.5:7b-instruct, temperature 0, JSON\n4 states · cờ y tế (health_alert) · crisis_flag · panic_flag\n(đọc tối đa 10 lượt user; chống prompt injection)", 120, 200, 320, 90, "llm")
    kw = d.node("Bộ keyword (chạy song song)\nTừ khoá thuốc → bật cờ y tế\nTừ khoá khủng hoảng → chỉ dự phòng khi LLM #1 lỗi", 580, 200, 300, 90, "proc")
    d.edge(u, api)
    d.edge(api, ext, "song song")
    d.edge(api, kw, "song song")
    d1 = d.node("crisis_flag?\n(hoặc LLM #1 lỗi\nvà keyword khủng hoảng)", X + 10, 330, 240, 110, "dec")
    d.edge(ext, d1)
    d.edge(kw, d1)
    cr = d.node("Phản hồi khủng hoảng soạn sẵn\nhỏi về an toàn, gọi 115 / cơ sở y tế, báo người thân\nĐường dây nóng Ngày Mai 096 306 1414, Tổng đài 111\n(+ hướng dẫn thở nếu có panic_flag)\nKHÔNG gọi LLM #2, KHÔNG gợi ý món", R, 330, 300, 110, "safe")
    d.edge(d1, cr, "Có")
    d2 = d.node("panic_flag?\n(đang hoảng loạn\nlúc chat)", X + 30, 480, 200, 100, "dec")
    d.edge(d1, d2, "Không")
    pn = d.node("Phản hồi hoảng loạn soạn sẵn\nthở 4-2-6, gọi tên 5 thứ đang thấy\ngọi 115 (113 nếu bị tấn công) khi đau ngực,\nkhó thở kéo dài, sắp ngất; kèm hotline\nKHÔNG gọi LLM #2", R, 475, 300, 110, "safe")
    d.edge(d2, pn, "Có")
    mg = d.node("Gộp states vào phiên\n(giá trị mới ghi đè, null giữ giá trị cũ)\nCờ y tế giữ suốt phiên", X, 620, W, 70, "proc")
    d.edge(d2, mg, "Không")
    d3 = d.node("Cờ y tế?\n(dùng thuốc hoặc\ncơ thể khác thường)", X + 30, 720, 200, 100, "dec")
    d.edge(mg, d3)
    med = d.node("Nhánh medication\nROUTE_NUTRITION: false\n+ SYSTEM_OVERRIDE (không gợi ý món,\nkhuyên hỏi bác sĩ đang điều trị)", L, 720, 260, 100, "branch")
    d.edge(d3, med, "Có")
    d4 = d.node("Còn thiếu state?\n(sleep, appetite,\nstress, mood)", X + 30, 850, 200, 100, "dec")
    d.edge(d3, d4, "Không")
    ask = d.node("Nhánh ask_states\nROUTE_NUTRITION: false\n+ MISSING_STATES (hỏi 1–2 state)", L, 850, 260, 90, "branch")
    d.edge(d4, ask, "Có")
    d5 = d.node("States có thay đổi\nso với lần gợi ý trước?", X + 20, 990, 220, 100, "dec")
    d.edge(d4, d5, "Không")
    side = d.node("Nhánh side_talk\nROUTE_NUTRITION: false", L, 1000, 260, 70, "branch")
    d.edge(d5, side, "Không")
    ret = d.node("Truy xuất (StateRetriever)\n1. state_effect_map: cộng trọng số theo đích tác động\n2. nutrition_support: 1 món thuộc đích cao nhất,\n   chưa gợi ý trong phiên, không bị loại (excluded);\n   gợi ý hết thì cho lặp lại\n3. CBT: bge-m3 + pgvector, so 2 lượt user gần nhất\n   và tin nhắn hiện tại với cbt_catalog", X - 40, 1115, 340, 165, "proc")
    d.edge(d5, ret, "Có")
    d6 = d.node("Có món phù hợp?", X + 30, 1300, 200, 80, "dec")
    d.edge(ret, d6)
    d.edge(d6, side, "Không")
    nut = d.node("Nhánh nutrition\nROUTE_NUTRITION: true\n+ NUTRITION_CONTEXT (NUT_xxx) + CBT_CONTEXT", X, 1410, W, 80, "branch")
    d.edge(d6, nut, "Có")
    pr = d.node("Dựng system prompt\nFIXED_PROMPT (giống từng ký tự dữ liệu train) + khối động\n+ 6 cặp lượt gần nhất (lượt assistant cũ = side_talk)", X - 20, 1530, 300, 80, "proc")
    d.edge(nut, pr)
    for b in (med, ask, side):
        d.edge(b, pr, extra="exitX=0.5;exitY=1;entryX=0;entryY=0.5;")
    gen = d.node("LLM #2 – qwen-huhu\nQwen2.5-7B-Instruct + LoRA, GGUF Q4_K_M\nOllama, temperature 0,3 → JSON\n(thought_process, side_talk, nutritional_advice, source_reference)", X - 20, 1650, 300, 90, "llm")
    d.edge(pr, gen)
    t1 = d.node("Guardrail tầng 1 đạt?\nJSON đủ khoá · side_talk không rỗng\ntrigger = ROUTE · không lẫn chữ Hán\nROUTE true: có advice + mã NUT_ thuộc context,\nkhông mg/g/kcal · ROUTE false: không khuyên ăn", X - 60, 1765, 380, 180, "dec")
    d.edge(gen, t1)
    rt = d.node("Còn lượt sinh lại?\n(tối đa 2 lần)", R + 50, 1800, 200, 100, "dec")
    d.edge(t1, rt, "Không")
    d.edge(rt, gen, "Có", extra="exitX=0.5;exitY=0;entryX=1;entryY=0.5;")
    fb = d.node("Sửa tối thiểu (repair) nếu có bản dùng được;\nnếu không: câu trả lời dự phòng\n(FALLBACK_REPLY, khuyên gặp chuyên gia)", R, 1950, 300, 80, "safe")
    d.edge(rt, fb, "Không")
    t2 = d.node("Guardrail tầng 2 – giám khảo gemma3:4b\n(khác gốc Qwen; chống prompt injection) đạt?", X - 10, 1960, 280, 120, "dec")
    d.edge(t1, t2, "Đạt")
    blk = d.node("Người dùng có rối loạn ăn uống /\nmang thai / triệu chứng cấp tính\n(hoặc giám khảo lỗi)\n→ bỏ gợi ý: sinh lại với ROUTE false", L - 10, 1960, 280, 90, "branch")
    d.edge(t2, blk, "chặn gợi ý món")
    d.edge(blk, pr, extra="exitX=0;exitY=0.5;entryX=0;entryY=0.25;")
    d.edge(t2, rt, "chẩn đoán / giọng gây hại /\ngợi ý món khi không được phép", extra="exitX=1;exitY=0.5;entryX=0.5;entryY=1;")
    outp = d.node("Câu trả lời = side_talk\n(+ nutritional_advice nếu ROUTE true)", X, 2120, W, 70, "out")
    d.edge(t2, outp, "Đạt")
    sv = d.node("Lưu phiên vào Redis (lịch sử, states, mã món đã gợi ý)\nGhi trace logs/turns.jsonl (cờ, prompt, output thô, lỗi guardrail từng lần thử)", X - 30, 2230, 320, 70, "proc")
    d.edge(outp, sv)
    d.edge(fb, sv)
    d.edge(cr, sv, extra="exitX=1;exitY=0.5;entryX=1;entryY=0.5;")
    d.edge(pn, sv, extra="exitX=1;exitY=0.5;entryX=1;entryY=0.5;")
    end = d.node("Gửi câu trả lời cho người dùng", X + 30, 2340, 200, 50, "term")
    d.edge(sv, end)
    # Kho dữ liệu và dịch vụ
    rd = d.node("Redis\n(phiên hội thoại)", 1150, 90, 150, 80, "db")
    pg = d.node("PostgreSQL 16 + pgvector\nnutrition_support (400 món, nut_code, excluded)\nstate_effect_map (14 dòng) · cbt_catalog (10)\npsychology_knowledge (988 đoạn, bge-m3)", 1100, 1110, 250, 140, "db")
    neo = d.node("Neo4j 5.18\n(đồ thị tri thức; dùng cho hybrid_retriever\nvà trực quan hoá, ngoài luồng chat)", 1100, 1300, 250, 110, "db")
    ol = d.node("Ollama 0.40.3\nqwen2.5:7b-instruct · qwen-huhu · gemma3:4b", 1100, 1650, 250, 90, "db")
    d.edge(api, rd, dashed=True)
    d.edge(sv, rd, dashed=True, extra="exitX=1;exitY=0.25;")
    d.edge(ret, pg, "SQL + vector", dashed=True)
    d.edge(gen, ol, dashed=True)
    d.node("Chú thích: tím = LLM; vàng = điều kiện; cam = nhánh định tuyến; đỏ = phản hồi an toàn soạn sẵn / dự phòng; "
           "xanh dương = xử lý; trụ xám = kho dữ liệu, dịch vụ; nét đứt = truy cập dữ liệu.", 40, 2420, 900, 40, "note")
    return d


# ====================================================================== DỮ LIỆU
def data():
    d = Diagram("Luồng dữ liệu")
    d.node("Luồng dữ liệu: từ nguồn thô đến model fine-tune, cơ sở dữ liệu RAG và đánh giá", 200, -70, 1100, 40, "title")
    # ---------------- Làn 1: dữ liệu hội thoại -> fine-tune
    d.node("1. Dữ liệu hội thoại → fine-tune LLM #2", 0, 0, 760, 2010, "lane")
    X = 220
    s1 = d.node("Nguồn hội thoại tư vấn tâm lý\n5.000 mẫu từ internet (dịch EN → VI theo MASTER_PROMPT_DICH)\n+ 1.000 mẫu do LLM sinh", X - 40, 50, 340, 80, "data")
    a1 = d.node("Lọc an toàn nhóm A (LLM #1 + keyword):\nkhủng hoảng, dùng thuốc, rối loạn ăn uống rõ", X - 20, 170, 300, 70, "proc")
    d.edge(s1, a1)
    sd = d.node("Tập test Safety Detector\n(mẫu khủng hoảng)", 540, 165, 190, 60, "safe")
    m3 = d.node("Mồi B3\n(mẫu dùng thuốc)", 540, 245, 190, 50, "branch")
    d.edge(a1, sd, "khủng hoảng")
    d.edge(a1, m3, "dùng thuốc")
    a2 = d.node("Làm sạch: bỏ dấu vết nhập vai, chuẩn hoá khoảng trắng,\nlọc gần trùng (cosine ≥ 0,9 trên embedding tin nhắn user)", X - 40, 280, 340, 70, "proc")
    d.edge(a1, a2, "còn lại")
    a3 = d.node("Fact-check các nhận định thực tế (Perplexity)\nSửa câu trả lời đã kiểm chứng: chỉ xoá / thêm câu, ghi log", X - 40, 380, 340, 70, "proc")
    d.edge(a2, a3)
    a4 = d.node("Chuyển format chuẩn: system prompt cố định + khối động,\nlượt cuối là chuỗi JSON (json.dumps)\nGán nhãn thought_process (API, few-shot, không mang lịch sử)", X - 40, 480, 340, 90, "proc")
    d.edge(a3, a4)
    a5 = d.node("side_talk < 20 từ\nvà không có câu hỏi?", X + 10, 600, 240, 100, "dec")
    d.edge(a4, a5)
    m1 = d.node("Mồi B1\n(câu trả lời quá ngắn)", 540, 620, 190, 60, "branch")
    d.edge(a5, m1, "Có")
    a6 = d.node("Chia nhóm A (mẫu cùng cụm nằm cùng phía):\n20% A-test (khoá, ưu tiên mẫu chuyên gia kiểm chứng)\n80% còn lại; chia mồi phụ B1, B3 theo 80/20", X - 40, 730, 340, 90, "proc")
    d.edge(a5, a6, "Không")
    b1 = d.node("Sinh nhóm B theo quy tắc (sau khi A-test đã chốt)\nB1 hỏi thêm state · B2 gợi ý món · B3 dùng thuốc · B4 bẫy hỏi ăn uống\nmồi A-train → B-train; mồi A-test → B-test; few-shot từ A-train\nB3 dùng / sửa bản bác sĩ duyệt", X - 60, 850, 380, 110, "llm")
    d.edge(a6, b1)
    d.edge(m1, b1, extra="exitX=0.5;exitY=1;entryX=1;entryY=0.25;")
    d.edge(m3, b1, extra="exitX=1;exitY=0.5;entryX=1;entryY=0.5;")
    qa = d.node("QA dữ liệu train (A và B):\ncheck_traindata.py – kiểm tra luật tự động\nfix_traindata.py – sửa có ghi log (3.546 thay đổi: reasoning,\ncâu hỏi state, khuyên đi khám, xưng hô, câu hứa hẹn…)\nfinalize_step2.py – bỏ 68 mẫu B2-train trùng B2-test;\nmẫu khủng hoảng / dùng thuốc → safetyguard.jsonl", X - 70, 985, 400, 145, "proc")
    d.edge(b1, qa)
    lg = d.node("traindata_logs/\ncheck_traindata · fix_traindata · finalize_step2\nchange_log.jsonl · removed_samples.jsonl", 550, 1005, 200, 100, "data")
    d.edge(qa, lg, dashed=True)
    sp = d.node("Tách validation 10% mỗi nhóm\nTrộn A-train + B-train (oversample B ×3), seed cố định\ntrain 6.847 · validation 750 · test 1.916\n(traindata/group_*.jsonl, test_*.jsonl)", X - 40, 1140, 340, 100, "proc")
    d.edge(qa, sp)
    ft = d.node("Fine-tune Qwen2.5-7B-Instruct + LoRA\n(r 16, alpha 32, mọi lớp linear; Kaggle TPU v5e-8, bf16)\nloss chỉ lượt assistant cuối; early stopping\nval loss tốt nhất 0,6687 → best_adapter", X - 40, 1270, 340, 100, "llm")
    d.edge(sp, ft)
    ex = d.node("Gộp LoRA vào model gốc → lượng tử GGUF Q4_K_M\n(export_gguf_kaggle) → Ollama: qwen-huhu", X - 40, 1400, 340, 70, "proc")
    d.edge(ft, ex)
    ev = d.node("Đánh giá model trên tập test (huhuevalu.ipynb)\nperplexity 11,23 → 2,41 · ROUGE-L 0,155 → 0,319\nBERTScore 0,872 → 0,908 · luật JSON 0% → 100%\nB3: 40/40 chuyển bác sĩ (13 người xác nhận)", X - 40, 1500, 340, 100, "out")
    d.edge(ft, ev, dashed=True, extra="exitX=1;exitY=0.5;entryX=1;entryY=0.5;")
    gr = d.node("Grounding và định tuyến qua nhiều lượt\ntrên test_B_B1..B4 (eval_grounding.py)", X - 40, 1630, 340, 60, "out")
    d.edge(sp, gr, "tập test", dashed=True, extra="exitX=0;exitY=0.5;entryX=0;entryY=0.5;")
    sysn = d.node("LLM #2 của hệ thống", X + 30, 1720, 200, 50, "term")
    d.edge(ex, sysn, extra="exitX=0.5;exitY=1;entryX=0;entryY=0.5;")

    # ---------------- Làn 2: dữ liệu RAG -> cơ sở dữ liệu
    d.node("2. Dữ liệu RAG → Hybrid Database", 800, 0, 620, 1100, "lane")
    r1 = d.node("Bảng thành phần thực phẩm VN FCT 2007 / USDA\n→ Data-to-Text: 400 data dinh duong.json\n(food_item, key_nutrients, ontology_effect, content_text)", 830, 50, 300, 90, "data")
    r2 = d.node("Tài liệu tâm lý CBT–CCI, MBSR, WHO PFA\ndịch EN → VI, chunk\n→ psychology_dataset_vi.json (988 đoạn)", 830, 160, 300, 80, "data")
    r3 = d.node("state_effect_map.json (14 dòng)\nstate → đích tác động + trọng số\ntheo ontology Xhani et al. (2026)\n+ excluded_foods (NUT_060)", 830, 260, 300, 90, "data")
    r4 = d.node("cbt_catalog.json\n10 kỹ thuật CBT / chánh niệm", 830, 370, 300, 60, "data")
    ing = d.node("ingestion/seed_all.py\ningest_postgres: schema.sql, nut_code (NUT_xxx theo thứ tự),\ncờ excluded, embedding bge-m3 (normalize)\ningest_neo4j: đồ thị Food → Nutrient → TargetFunction", 830, 470, 360, 100, "proc")
    for r in (r1, r2, r3, r4):
        d.edge(r, ing, extra="exitX=1;exitY=0.5;entryX=1;entryY=0.5;")
    pg = d.node("PostgreSQL 16 + pgvector\nnutrition_support · state_effect_map\ncbt_catalog · psychology_knowledge", 860, 610, 250, 110, "db")
    neo = d.node("Neo4j 5.18\n(435 node; trực quan hoá,\nhybrid_retriever)", 1170, 610, 220, 110, "db")
    d.edge(ing, pg)
    d.edge(ing, neo)
    chk = d.node("Kiểm tra: số dòng khớp file; 988 đoạn đều có embedding;\ntruy xuất PostgreSQL = bản JSON trên 384 tổ hợp state", 830, 760, 360, 70, "proc")
    d.edge(pg, chk, dashed=True)
    sysr = d.node("Truy xuất của hệ thống\n(StateRetriever)", 900, 870, 200, 60, "term")
    d.edge(pg, sysr, extra="exitX=0;exitY=0.5;entryX=0;entryY=0.5;")

    # ---------------- Làn 3: đánh giá và kiểm chứng
    d.node("3. Kiểm chứng và đánh giá", 800, 1140, 620, 870, "lane")
    rv = d.node("sample_for_experts.py: lấy ngẫu nhiên phân tầng 40 mẫu\n(fine-tune, QA tự sinh, kho dinh dưỡng, kho tâm lý)\n→ 6 người chấm độc lập (Likert 1–5 + cột chọn)", 830, 1190, 360, 90, "proc")
    d.edge(r1, rv, dashed=True, extra="exitX=0;exitY=0.5;entryX=0;entryY=0.5;")
    ag = d.node("expert_agreement.py: Fleiss' κ, Krippendorff's α, Gwet's AC\n→ TONG_KET_CHUYEN_GIA.md", 830, 1310, 360, 60, "out")
    d.edge(rv, ag)
    ts = d.node("3 bộ test 300 câu (crisis, retrieval, safety)\nchỉ chạy một lần trên hệ thống đã cố định;\nkhông dùng để viết prompt, từ khoá, luật", 830, 1410, 360, 80, "data")
    pk = d.node("make_kaggle_package.py: gói hệ thống + manifest sha256\n→ Kaggle (T4 ×2): kiểm sha256 file, GGUF, digest model, bge-m3\n→ dựng PostgreSQL, Redis, Neo4j, Ollama → seed → unit test", 830, 1520, 360, 90, "proc")
    d.edge(ts, pk)
    rs = d.node("eval_system.py · eval_baselines.py (P, B1, B2, B3) · eval_grounding.py\n→ giám khảo gemma3:4b → analyze_final.py (số chính thức)\n→ chấm tay các ca trượt (chỉ để phân tích lỗi)\n→ BAO_CAO_DANH_GIA.md · BAO_CAO_KET_QUA_CUOI.docx", 830, 1640, 360, 100, "out")
    d.edge(pk, rs)
    d.node("Chú thích: tài liệu xám = file dữ liệu; tím = bước dùng LLM; vàng = điều kiện; cam = mồi cho nhóm B; "
           "đỏ = tập test an toàn; xanh lá = đầu ra / kết quả; nét đứt = dùng làm đầu vào phụ hoặc kiểm tra.", 0, 2030, 1400, 40, "note")
    return d


def main():
    for d, name in ((system(), "flowchart_he_thong.drawio"), (data(), "flowchart_du_lieu.drawio")):
        p = os.path.join(AIM, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(d.xml())
        print(p, len(d.cells), "phần tử")


if __name__ == "__main__":
    main()
