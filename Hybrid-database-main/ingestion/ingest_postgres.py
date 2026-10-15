import os
import sys
import json
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

def get_pg_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "mental_nutrition_db"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "password123"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def init_postgres_schema(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("""
            ALTER TABLE nutrition_support ALTER COLUMN ontology_effect DROP NOT NULL;
            ALTER TABLE nutrition_support ALTER COLUMN content_text DROP NOT NULL;
        """)
    conn.commit()
    print("[PostgreSQL] Đã khởi tạo schema.sql thành công.")

def ingest_nutrition_table(conn, data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE nutrition_support RESTART IDENTITY;")
        for i, item in enumerate(items, 1):
            cur.execute("""
                INSERT INTO nutrition_support (food_item, key_nutrients, ontology_effect, content_text, source_reference, nut_code)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                item.get("food_item", ""),
                item.get("key_nutrients") or [],
                item.get("ontology_effect"),
                item.get("content_text"),
                item.get("source_reference", ""),
                f"NUT_{i:03d}"
            ))
    conn.commit()
    print(f"[PostgreSQL] Đã nạp thành công {len(items)} bản ghi từ '400 data dinh duong.json' vào bảng 'nutrition_support'.")

def ingest_state_effect_map(conn, data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE state_effect_map;")
        for m in cfg["map"]:
            cur.execute("""
                INSERT INTO state_effect_map (state_name, state_value, target_function, weight)
                VALUES (%s, %s, %s, %s);
            """, (m["state"], m["value"], m["target"], m.get("weight", 1.0)))
        cur.execute("UPDATE nutrition_support SET excluded = (nut_code = ANY(%s::text[]));", (cfg.get("excluded_foods", []),))
    conn.commit()
    print(f"[PostgreSQL] Đã nạp {len(cfg['map'])} dòng state_effect_map, loại {len(cfg.get('excluded_foods', []))} thực phẩm khỏi gợi ý.")

def ingest_cbt_catalog(conn, data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)["items"]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE cbt_catalog;")
        for it in items:
            cur.execute("INSERT INTO cbt_catalog (chunk_id, title, summary) VALUES (%s, %s, %s);",
                        (it["chunk_id"], it["title"], it["summary"]))
    conn.commit()
    print(f"[PostgreSQL] Đã nạp {len(items)} kỹ thuật vào bảng 'cbt_catalog'.")

def ingest_psychology_vectors(conn, data_path, model_name=None):
    if model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")

    print(f"[PostgreSQL] Đang tải mô hình embedding: {model_name}...")
    embed_model = SentenceTransformer(model_name, model_kwargs={"use_safetensors": True})

    with open(data_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE psychology_knowledge RESTART IDENTITY;")
        for chunk in chunks:
            # Nhúng vector cho đoạn văn bản
            emb = embed_model.encode(chunk.get("content_text", ""), normalize_embeddings=True).tolist()
            cur.execute("""
                INSERT INTO psychology_knowledge (chunk_id, target_mental_state, tags, content_text, source_reference, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO NOTHING;
            """, (
                chunk.get("chunk_id", ""),
                chunk.get("target_mental_state", ""),
                chunk.get("tags", []),
                chunk.get("content_text", ""),
                chunk.get("source_reference", ""),
                emb
            ))
    conn.commit()
    print(f"[PostgreSQL] Đã nhúng vector và nạp {len(chunks)} đoạn từ 'psychology_dataset_vi.json' vào bảng 'psychology_knowledge'.")

def run_postgres_ingestion():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nutr_file = os.path.join(base_dir, "data", "processed", "400 data dinh duong.json")
    psy_file = os.path.join(base_dir, "data", "processed", "psychology_dataset_vi.json")
    map_file = os.path.join(base_dir, "data", "processed", "state_effect_map.json")
    cbt_file = os.path.join(base_dir, "data", "processed", "cbt_catalog.json")

    conn = get_pg_conn()
    init_postgres_schema(conn)
    ingest_nutrition_table(conn, nutr_file)
    ingest_state_effect_map(conn, map_file)
    ingest_cbt_catalog(conn, cbt_file)
    ingest_psychology_vectors(conn, psy_file)
    conn.close()
    print("[PostgreSQL] Ingestion toàn bộ hoàn tất 100%!")

if __name__ == "__main__":
    run_postgres_ingestion()
