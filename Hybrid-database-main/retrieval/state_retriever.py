"""Truy xuất context cho LLM #2 theo 4 states, xuất đúng định dạng dữ liệu fine-tune:

    [NUTRITION_CONTEXT]: NUT_306 – Hải sâm | Tryptophan | REGULATING | điều hòa dẫn truyền thần kinh
    [CBT_CONTEXT]:       PSY_MINDFUL_0001 – Nhận thức hơi thở (Breath Awareness) | Quan sát và nhận diện ...

- Thực phẩm: SQL trên nutrition_support JOIN state_effect_map (PostgreSQL).
- Kỹ thuật CBT: vector search (pgvector, BGE-M3) trong danh mục cbt_catalog.
"""
import json
import os
import random
import re
from collections import defaultdict

MECHANISM_VI = {
    ("INHIBITING", "stress_response"): "kìm hãm phản ứng căng thẳng",
    ("REDUCING", "stress_response"): "giảm phản ứng căng thẳng",
    ("REGULATING", "neurotransmission"): "điều hòa dẫn truyền thần kinh",
    ("REDUCING", "mood_regulation"): "điều hòa tâm trạng",
    ("REGULATING", "mood_regulation"): "điều hòa tâm trạng",
    ("REGULATING", "digestion"): "điều hòa tiêu hóa",
}
TARGET_VI = {"stress_response": "phản ứng căng thẳng", "neurotransmission": "dẫn truyền thần kinh",
             "mood_regulation": "tâm trạng", "digestion": "tiêu hóa"}
ACTION_VI = {"INHIBITING": "kìm hãm", "REDUCING": "giảm", "REGULATING": "điều hòa"}


def nut_code(index_1based):
    return f"NUT_{index_1based:03d}"


def split_effect(ontology_effect):
    action, _, target = (ontology_effect or "").partition(":")
    return action.strip(), target.strip()


def primary_nutrient(key_nutrients, content_text):
    """Hoạt chất chính là chất đứng trước 'có tác dụng' trong content_text (khớp tên đầy đủ trong key_nutrients)."""
    nutrients = [n for n in (key_nutrients or []) if not n.startswith("(")]
    m = re.search(r"\.\s*(.+?) có tác dụng", content_text or "")
    if m:
        name = m.group(1).strip()
        for n in nutrients:
            if n == name or n.startswith(name):
                return n
        return name
    return nutrients[0] if nutrients else ""


def format_nutrition_line(code, food_item, key_nutrients, ontology_effect, content_text):
    action, target = split_effect(ontology_effect)
    mech = MECHANISM_VI.get((action, target)) or f"{ACTION_VI.get(action, action.lower())} {TARGET_VI.get(target, target)}"
    return f"{code} – {food_item} | {primary_nutrient(key_nutrients, content_text)} | {action} | {mech}"


def format_cbt_line(chunk_id, title, summary):
    return f"{chunk_id} – {title} | {summary}"


class StateRetriever:
    def __init__(self, conn_factory=None, embed_model_name=None, cbt_min_similarity=0.0):
        if conn_factory is None:
            from db.db_clients import DatabaseClients
            conn_factory = DatabaseClients.get_pg_connection
        self._conn_factory = conn_factory
        self._embed_model_name = embed_model_name or os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
        self._embedder = None
        self.cbt_min_similarity = cbt_min_similarity

    def _query(self, sql, params):
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            conn.commit()
            return rows
        except Exception:
            conn.rollback()
            raise

    def target_weights(self, keys):
        """Tổng trọng số theo đích tác động (chỉ các đích có món trong bảng), giống OfflineStateRetriever."""
        rows = self._query("""
            SELECT m.target_function, SUM(m.weight) FROM state_effect_map m
            WHERE m.state_name || ':' || m.state_value = ANY(%s::text[])
              AND m.target_function IN (
                  SELECT DISTINCT btrim(split_part(n.ontology_effect, ':', 2)) FROM nutrition_support n
                  WHERE n.ontology_effect IS NOT NULL AND NOT n.excluded AND n.nut_code IS NOT NULL)
            GROUP BY m.target_function;""", (list(keys),))
        return {r[0]: float(r[1]) for r in rows}

    def _foods(self, keys, exclude, k):
        return self._query("""
            WITH t AS (
                SELECT target_function, SUM(weight) AS w FROM state_effect_map
                WHERE state_name || ':' || state_value = ANY(%s::text[])
                GROUP BY target_function)
            SELECT n.nut_code, n.food_item, n.key_nutrients, n.ontology_effect, n.content_text, t.w
            FROM nutrition_support n
            JOIN t ON t.target_function = btrim(split_part(n.ontology_effect, ':', 2))
            WHERE n.ontology_effect IS NOT NULL AND NOT n.excluded AND n.nut_code IS NOT NULL
              AND NOT (n.nut_code = ANY(%s::text[]))
            ORDER BY t.w DESC, random()
            LIMIT %s;""", (list(keys), list(exclude), k))

    def nutrition(self, states, exclude_codes=(), k=1):
        """states: {"sleep_state": "Poor", ...}. Trả [{"code", "food_item", "line"}]; ưu tiên món chưa gợi ý."""
        keys = [f"{s}:{v}" for s, v in states.items() if v]
        rows = self._foods(keys, exclude_codes, k) or self._foods(["*:*"], exclude_codes, k)
        if not rows and exclude_codes:  # đã gợi ý hết món phù hợp: cho phép lặp lại
            rows = self._foods(keys, [], k) or self._foods(["*:*"], [], k)
        return [{"code": r[0], "food_item": r[1], "line": format_nutrition_line(r[0], r[1], r[2], r[3], r[4])}
                for r in rows]

    def cbt(self, query_text):
        """Kỹ thuật CBT/chánh niệm gần nhất với hội thoại (trong cbt_catalog), hoặc None."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self._embed_model_name, model_kwargs={"use_safetensors": True})
        vec = self._embedder.encode(query_text, normalize_embeddings=True).tolist()
        # MATERIALIZED: so trực tiếp trên ~10 kỹ thuật trong danh mục. Nếu đi qua chỉ mục HNSW, pgvector chỉ lấy
        # ~40 đoạn gần nhất trong toàn bảng (hnsw.ef_search) rồi mới lọc theo cbt_catalog, nên thường ra rỗng.
        rows = self._query("""
            WITH c AS MATERIALIZED (
                SELECT c.chunk_id, c.title, c.summary, p.embedding
                FROM cbt_catalog c JOIN psychology_knowledge p ON p.chunk_id = c.chunk_id)
            SELECT chunk_id, title, summary, 1 - (embedding <=> %s::vector) AS sim
            FROM c
            ORDER BY embedding <=> %s::vector
            LIMIT 1;""", (vec, vec))
        if not rows or rows[0][3] < self.cbt_min_similarity:
            return None
        return format_cbt_line(rows[0][0], rows[0][1], rows[0][2])


class OfflineStateRetriever:
    """Bản chạy không cần PostgreSQL: đọc thẳng các file JSON, cùng logic chọn món với câu SQL ở trên.
    Không có CBT_CONTEXT (cần pgvector). Dùng để test khi chưa bật Docker: RETRIEVER=offline."""

    def __init__(self, data_dir=None):
        base = data_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
        with open(os.path.join(base, "400 data dinh duong.json"), encoding="utf-8") as f:
            foods = json.load(f)
        with open(os.path.join(base, "state_effect_map.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        excluded = set(cfg.get("excluded_foods", []))
        self.foods = [(nut_code(i), f) for i, f in enumerate(foods, 1)
                      if f.get("ontology_effect") and nut_code(i) not in excluded]
        self.map = cfg["map"]

    def target_weights(self, keys):
        """Tổng trọng số theo đích tác động (chỉ các đích có món trong bảng)."""
        have = {split_effect(f["ontology_effect"])[1] for _, f in self.foods}
        w = defaultdict(float)
        for r in self.map:
            if f"{r['state']}:{r['value']}" in keys and r["target"] in have:
                w[r["target"]] += r["weight"]
        return dict(w)

    def _foods(self, keys, exclude, k):
        w = self.target_weights(set(keys))
        cands = [(w[split_effect(f["ontology_effect"])[1]], code, f) for code, f in self.foods
                 if split_effect(f["ontology_effect"])[1] in w and code not in exclude]
        random.shuffle(cands)
        cands.sort(key=lambda c: -c[0])
        return cands[:k]

    def nutrition(self, states, exclude_codes=(), k=1):
        keys = [f"{s}:{v}" for s, v in states.items() if v]
        rows = self._foods(keys, set(exclude_codes), k) or self._foods(["*:*"], set(exclude_codes), k)
        if not rows and exclude_codes:
            rows = self._foods(keys, set(), k) or self._foods(["*:*"], set(), k)
        return [{"code": code, "food_item": f["food_item"],
                 "line": format_nutrition_line(code, f["food_item"], f["key_nutrients"], f["ontology_effect"], f["content_text"])}
                for _, code, f in rows]

    def cbt(self, query_text):
        return None
