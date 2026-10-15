import os
import sys
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db_clients import DatabaseClients

load_dotenv()

# Bảng ánh xạ từ Triệu chứng thường gặp sang Target Functions của Ontology
SYMPTOM_TO_ONTOLOGY = {
    "stress": "stress_response",
    "căng thẳng": "stress_response",
    "lo âu": "stress_response",
    "bồn chồn": "stress_response",
    "đau đầu": "stress_response",
    "mất ngủ": "sleep_regulation",
    "khó ngủ": "sleep_regulation",
    "trằn trọc": "sleep_regulation",
    "buồn": "mood_regulation",
    "trầm cảm": "mood_regulation",
    "chán nản": "mood_regulation",
    "mệt mỏi": "neurotransmission",
    "uể oải": "physical_activity_behavior",
    "đau dạ dày": "digestion",
    "đầy hơi": "digestion",
    "thèm ăn": "appetite_regulation",
    "chán ăn": "appetite_regulation",
    "nóng nảy": "impulsivity_control",
    "cáu gắt": "impulsivity_control"
}

class HybridRetriever:
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
        
        print(f"[HybridRetriever] Đang khởi tạo mô hình embedding: {model_name}...")
        self.embed_model = SentenceTransformer(model_name, model_kwargs={"use_safetensors": True})
        self.pg_conn = DatabaseClients.get_pg_connection()
        self.neo_driver = DatabaseClients.get_neo4j_driver()

    def retrieve(self, symptoms: List[str], emotions: str = "") -> Dict[str, Any]:
        """
        Truy xuất Context kết hợp:
        1. Graph RAG (Neo4j): Mạng lưới Thực phẩm -> Vi chất -> Đích tác động
        2. SQL Exact Filter (Postgres): Bảng 400 thực phẩm định tính
        3. Vector Search (pgvector): Kho tri thức 988 đoạn tâm lý học
        """
        results = {
            "graph_facts": [],
            "sql_food_docs": [],
            "vector_psy_docs": [],
            "formatted_context": ""
        }

        # Xác định Target Functions từ triệu chứng người dùng
        target_funcs = set()
        for sym in symptoms:
            sym_clean = sym.lower().strip()
            for k, v in SYMPTOM_TO_ONTOLOGY.items():
                if k in sym_clean:
                    target_funcs.add(v)

        target_funcs_list = list(target_funcs) if target_funcs else ["stress_response", "mood_regulation"]

        # 1. TRUY VẤN GRAPH RAG (Neo4j)
        cypher_query = """
        MATCH (t:TargetFunction)<-[e:HAS_EFFECT]-(n:Nutrient)<-[:CONTAINS]-(f:Food)
        WHERE t.name IN $targets
        RETURN DISTINCT f.name AS food, n.name AS nutrient, e.action AS action, e.full_effect AS full_effect, t.name AS target_func
        LIMIT 5
        """
        try:
            with self.neo_driver.session() as session:
                res = session.run(cypher_query, targets=target_funcs_list)
                for r in res:
                    fact_str = f"{r['food']} chứa {r['nutrient']} có tác dụng {r['action']} hỗ trợ {r['target_func']} ({r['full_effect']})"
                    results["graph_facts"].append(fact_str)
        except Exception as e:
            print(f"[HybridRetriever] Thông báo Graph RAG: {e}")

        # 2. TRUY VẤN SQL TABLE (Bảng 400 Thực phẩm)
        try:
            with self.pg_conn.cursor() as cur:
                cur.execute("""
                    SELECT food_item, content_text, source_reference
                    FROM nutrition_support
                    WHERE ontology_effect ILIKE ANY(%s)
                    LIMIT 3;
                """, ([f"%{tf}%" for tf in target_funcs_list],))
                rows = cur.fetchall()
                for r in rows:
                    results["sql_food_docs"].append({
                        "food_item": r[0],
                        "content_text": r[1],
                        "source_reference": r[2]
                    })
        except Exception as e:
            print(f"[HybridRetriever] Thông báo SQL: {e}")

        # 3. TRUY VẤN VECTOR SEARCH (Kho 988 tri thức tâm lý)
        query_text = f"Tâm trạng: {emotions}. Triệu chứng: {', '.join(symptoms)}" if symptoms else emotions
        if query_text:
            try:
                query_vec = self.embed_model.encode(query_text).tolist()
                with self.pg_conn.cursor() as cur:
                    cur.execute("""
                        SELECT target_mental_state, content_text, source_reference
                        FROM psychology_knowledge
                        ORDER BY embedding <=> %s::vector
                        LIMIT 1;
                    """, (query_vec,))
                    v_row = cur.fetchone()
                    if v_row:
                        results["vector_psy_docs"].append({
                            "state": v_row[0],
                            "content_text": v_row[1],
                            "source_reference": v_row[2]
                        })
            except Exception as e:
                print(f"[HybridRetriever] Thông báo Vector: {e}")

        # 4. TỔNG HỢP THÀNH CHUỖI CONTEXT CHUẨN NẠP CHO GENERATOR
        context_lines = []
        if results["graph_facts"]:
            context_lines.append("=== 1. QUAN HỆ SUY LUẬN DINH DƯỠNG (GRAPH RAG) ===")
            for fact in results["graph_facts"]:
                context_lines.append(f"• {fact}")

        if results["sql_food_docs"]:
            context_lines.append("\n=== 2. MÔ TẢ THỰC PHẨM ĐỊNH TÍNH KIỂM CHỨNG (BẢNG VN FCT 2007 / USDA) ===")
            for doc in results["sql_food_docs"]:
                context_lines.append(f"• {doc['food_item']}: {doc['content_text']} [Nguồn: {doc['source_reference']}]")

        if results["vector_psy_docs"]:
            context_lines.append("\n=== 3. CƠ SỞ TRI THỨC TÂM LÝ & THẦN KINH ===")
            for doc in results["vector_psy_docs"]:
                context_lines.append(f"• [{doc['state']}]: {doc['content_text']} [Nguồn: {doc['source_reference']}]")

        results["formatted_context"] = "\n".join(context_lines)
        return results
