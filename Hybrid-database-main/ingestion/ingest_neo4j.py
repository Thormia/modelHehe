import os
import sys
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

def get_neo4j_driver():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
    )

def init_neo4j_constraints(driver):
    cypher_path = os.path.join(os.path.dirname(__file__), "..", "db", "graph_schema.cypher")
    with open(cypher_path, "r", encoding="utf-8") as f:
        statements = f.read().split(";")

    with driver.session() as session:
        for stmt in statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith("//"):
                try:
                    session.run(stmt)
                except Exception as e:
                    pass
    print("[Neo4j] Đã khởi tạo Constraints và Lược đồ đồ thị thành công.")

def ingest_graph_data(driver, data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    with driver.session() as session:
        # Xóa dữ liệu cũ
        session.run("MATCH (n) DETACH DELETE n")

        for item in items:
            food = item.get("food_item", "")
            effect = item.get("ontology_effect")
            nutrients = item.get("key_nutrients") or []

            # 1. Tạo Node Food
            session.run("MERGE (f:Food {name: $food})", food=food)

            # Nếu không có effect hoặc dưới ngưỡng 20% DV, chỉ giữ node Food
            if not effect:
                continue

            # Bóc tách Động từ và Target Function từ ontology_effect (VD: "INHIBITING: stress_response")
            if ":" in effect:
                parts = effect.split(":")
                action = parts[0].strip()
                target_func = parts[1].strip()
            else:
                action = effect.strip()
                target_func = "general_wellbeing"

            # 2. Tạo Node TargetFunction (Đích tác động sinh hóa / tâm lý)
            session.run("MERGE (t:TargetFunction {name: $target_func})", target_func=target_func)

            for nutrient in nutrients:
                # Bỏ qua các chuỗi chú thích dạng "(dưới ngưỡng 20% DV...)"
                if nutrient.startswith("("):
                    continue
                # 3. Tạo Node Nutrient & Liên kết (Food)-[:CONTAINS]->(Nutrient)
                session.run("""
                    MERGE (n:Nutrient {name: $nutrient})
                    WITH n
                    MATCH (f:Food {name: $food})
                    MERGE (f)-[:CONTAINS]->(n)
                """, nutrient=nutrient, food=food)

                # 4. Tạo Liên kết (Nutrient)-[:HAS_EFFECT]->(TargetFunction)
                session.run("""
                    MATCH (n:Nutrient {name: $nutrient})
                    MATCH (t:TargetFunction {name: $target_func})
                    MERGE (n)-[:HAS_EFFECT {action: $action, full_effect: $effect}]->(t)
                """, nutrient=nutrient, target_func=target_func, action=action, effect=effect)

    print(f"[Neo4j] Đã nạp thành công Đồ thị tri thức từ {len(items)} thực phẩm trong '400 data dinh duong.json' vào Graph Database.")

def run_neo4j_ingestion():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nutr_file = os.path.join(base_dir, "data", "processed", "400 data dinh duong.json")

    driver = get_neo4j_driver()
    init_neo4j_constraints(driver)
    ingest_graph_data(driver, nutr_file)
    driver.close()
    print("[Neo4j] Ingestion hoàn tất 100%!")

if __name__ == "__main__":
    run_neo4j_ingestion()
